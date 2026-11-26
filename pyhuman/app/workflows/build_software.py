import os
import random
import re
from ..utility.human_typer import HumanTyperShell
from ..utility.shell_interact import run_shell_commands_with_checks
from ..utility.metric_workflow import MetricWorkflow


WORKFLOW_NAME = 'BuildSoftware'
WORKFLOW_DESCRIPTION = 'Pick a random piece of software, download it, install prereqs, and build the software'

# Offline package store.
#
# Empty unless RBP phase 1 staged one, so every helper below falls through to
# the upstream URL and an online run is byte-for-byte what it was.
#
# The file is read directly rather than trusting the environment: pyhuman is
# launched from a non-interactive context that does not source
# /etc/profile.d.
def _offline_base():
    base = (os.environ.get('CASTLE_OFFLINE_BASE') or '').strip()
    if not base:
        try:
            with open('/etc/profile.d/castle-offline.sh') as fh:
                for line in fh:
                    if line.startswith('export CASTLE_OFFLINE_BASE='):
                        base = line.split('=', 1)[1].strip().strip('"').strip("'")
        except OSError:
            base = ''
    return base.rstrip('/')


def _clone_step(name, online_cmd, online_pattern=r"Cloning into"):
    """
    A git clone online; the mirrored shallow archive offline.

    The archive is built with `git archive --prefix=<name>/`, so it extracts
    to the same directory the clone would have produced and the `cd <name>`
    step that follows is identical either way.

    The expected-output pattern has to change with the command: "Cloning
    into" never appears when the source arrives as a tarball, and leaving it
    in place would fail a step that actually succeeded.
    """
    base = _offline_base()
    if not base:
        return (online_cmd, online_pattern)
    # Positive proof, not r".*".
    #
    # r".*" matches the output of a command that did nothing. pyhuman types
    # with deliberate typos, so a mangled `curl` downloads nothing, the step
    # is still scored "success", and the failure surfaces two steps later at
    # `cd <name>` -- which is exactly how build_software failed the first
    # air-gapped run that got far enough to run it. The comment under
    # cmd_no_err below records someone fixing this same class of bug for
    # setup steps; this reintroduced it.
    #
    # Echoing a token only reachable after a non-empty download and a
    # successful extract means a mistyped command scores "retry", which is
    # what the typo simulation needs.
    return ("curl -sfL -o {0}.tar.gz {1}/src/{0}.tar.gz && tar xzf {0}.tar.gz "
            "&& test -d {0} && echo CASTLE_FETCHED_{0}".format(name, base),
            r"CASTLE_FETCHED_{0}".format(name))


def _fetch_step(filename, online_cmd, online_pattern=r"Saving to"):
    """A wget/curl of a source tarball online; the stored copy offline."""
    base = _offline_base()
    if not base:
        return (online_cmd, online_pattern)
    # Same reasoning as _clone_step: prove the file arrived and is non-empty
    # rather than accepting any output at all.
    return ("curl -sfL -O {0}/files/build_software/{1} && test -s {1} "
            "&& echo CASTLE_FETCHED_{1}".format(base, filename),
            r"CASTLE_FETCHED_{0}".format(re.escape(filename)))


# Define basic success check using regex


def basic_success(pattern): return lambda task, output, fail_count: (
    "success"
    if re.search(pattern, output)
    else ("retry" if fail_count < 2 else "fail")
)


# Stricter check for setup steps (`mkdir <dir>`, `cd <dir>`, etc.) where the
# previous default `r".*"` matched any output -- including obvious shell
# errors. That silently let workflows continue past a broken pre-step and
# fail later in a confusing place. cmd_no_err returns "success" only if
# none of the well-known error fragments appear in the output.
_CMD_ERROR_PATTERNS = [
    r'[Pp]ermission denied',
    r'No such file or directory',
    r'command not found',
    r'cannot create',
    r'Operation not permitted',
    r'Read-only file system',
]
def cmd_no_err(task, output, fail_count):
    for pat in _CMD_ERROR_PATTERNS:
        if re.search(pat, output):
            return "retry" if fail_count < 2 else "fail"
    return "success"


def cmds(blocks):
    def get_check(p):
        return basic_success(p) if isinstance(p, str) else p
    return [[{"command": c, "check": get_check(p)} for c, p in group] for group in blocks]

# Example check function for tar-based build


def tarball_check_contains(string):
    def check(task, output, fail_count):
        return "success" if string in output else ("retry" if fail_count < 2 else "fail")
    return check


# Software project definitions
#
# Clones are --depth 1: these workflows build the tip, never consult history,
# and emulate-logins runs them inside a 60 s login window under --fast-debug
# (it forces login_length = 60). A full clone of neovim or tmux spends most of
# that window fetching history nobody looks at. micro was already shallow.
software_projects = cmds([
    [
        ("rm -rf htop*", r".*"),
        _clone_step("htop", "git clone --depth 1 https://github.com/htop-dev/htop.git", r"Cloning into"),
        ("cd htop", cmd_no_err),
        ("./autogen.sh", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"gcc .* -o htop "),
        ("./htop --help", r"-no-color"),
    ],
    [
        ("rm -rf jq*", r".*"),
        _clone_step("jq", "git clone --depth 1 https://github.com/jqlang/jq.git", r"Cloning into"),
        ("cd jq", cmd_no_err),
        ("git submodule update --init", r"Submodule|Checking out files"),
        ("autoreconf -fi", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"GEN +src/version\.h"),
        ("./jq --help", r"jq - commandline JSON processor"),
    ],
    [
        ("rm -rf tmux*", r".*"),
        _clone_step("tmux", "git clone --depth 1 https://github.com/tmux/tmux.git", r"Cloning into"),
        ("cd tmux", cmd_no_err),
        ("sh autogen.sh", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"tmux"),
        ("./tmux -V", r"tmux"),
    ],
    [
        # Pin micro to v2.0.11 (May 2022). master/HEAD bumped go.mod to
        # `go 1.19` and started using fmt.Append, which Jammy's Go 1.18
        # rejects at compile time ("undefined: fmt.Append"). v2.0.11 is
        # the last release whose go.mod still says `go 1.16`.
        ("rm -rf micro*", r".*"),
        _clone_step("micro", "git clone --branch v2.0.11 --depth 1 https://github.com/zyedidia/micro.git", r"Cloning into"),
        ("cd micro", cmd_no_err),
        ("make ", r"go build"),
        ("./micro --help", r"Usage: micro"),
    ],
    [
        ("rm -rf neovim*", r".*"),
        _clone_step("neovim", "git clone --depth 1 https://github.com/neovim/neovim.git", r"Cloning into"),
        ("cd neovim", cmd_no_err),
        ("make CMAKE_BUILD_TYPE=Release -j", r"Generating doc/tags"),
        ("./build/bin/nvim --version", r"NVIM"),
    ],
    [
        ("rm -rf wget*", r".*"),
        ("mkdir wget", cmd_no_err),
        ("cd wget", cmd_no_err),
        _fetch_step("wget-1.21.4.tar.gz", "wget https://ftpmirror.gnu.org/gnu/wget/wget-1.21.4.tar.gz", r"Saving to"),
        ("tar xf wget-1.21.4.tar.gz", r".*"),
        ("cd wget-1.21.4", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j", r"Built target|make\[.*\]"),
        ("src/wget --help", tarball_check_contains("Usage: wget")),
    ],
    [
        ("rm -rf man-db*", r".*"),
        _fetch_step("man-db-2.12.0.tar.xz", "wget https://download.savannah.gnu.org/releases/man-db/man-db-2.12.0.tar.xz", r"Saving to"),
        ("tar xf man-db-2.12.0.tar.xz", r".*"),
        ("cd man-db-2.12.0", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./src/man --help", tarball_check_contains("Usage: man")),
    ],
    [
        ("rm -rf xz*", r".*"),
        _fetch_step("xz-5.4.5.tar.gz",
                    "curl -LO https://tukaani.org/xz/xz-5.4.5.tar.gz",
                    r"Average Speed   Time    Time     Time  Current"),
        ("tar xf xz-5.4.5.tar.gz", r".*"),
        ("cd xz-5.4.5", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./src/xz/xz --help", tarball_check_contains("XZ Utils home page")),
    ],
    [
        ("rm -rf ncurses*", r".*"),
        _fetch_step("ncurses-6.4.tar.gz", "wget https://ftpmirror.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz", r"Saving to"),
        ("tar xf ncurses-6.4.tar.gz", r".*"),
        ("cd ncurses-6.4", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j$(nproc)", r"make\[.*\]|CC"),
        ("./progs/tput --help", tarball_check_contains("Usage")),
    ],
    [
        ("rm -rf sbase*", r".*"),
        _clone_step("sbase", "git clone git://git.suckless.org/sbase", r"Cloning into"),
        ("cd sbase", cmd_no_err),
        ("make -j", r"c99"),
        ("./ls --help || true", r"usage|Usage|invalid option"),
    ],
    [
        ("rm -rf zutils*", r".*"),
        _fetch_step("zutils-1.11.tar.lz", "wget https://download.savannah.gnu.org/releases/zutils/zutils-1.11.tar.lz", r"Saving to"),
        ("tar --lzip -xf zutils-1.11.tar.lz", r".*"),
        ("cd zutils-1.11", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j", r"-o zcat"),
        ("./zcat --help", tarball_check_contains("Usage: zcat")),
    ],
    [
        ("rm -rf bash*", r".*"),
        _fetch_step("bash-5.2.15.tar.gz", "wget https://ftpmirror.gnu.org/gnu/bash/bash-5.2.15.tar.gz", r"Saving to"),
        ("tar xf bash-5.2.15.tar.gz", r".*"),
        ("cd bash-5.2.15", cmd_no_err),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./bash --version", tarball_check_contains("GNU bash")),
    ]
])


def load():
    # build_software shells out to apt-get / git / configure / make and
    # uses a POSIX pty to drive the interactive shell -- Linux-only by
    # design. Skip on Windows so the workflow gets excluded from the
    # random pool instead of failing instantly with an uncaught
    # exception on every cluster iteration (and inflating the body-error
    # count without producing any actual workload on the fileserver).
    if os.name != 'posix':
        return None
    return BuildSoftware()


class BuildSoftware(MetricWorkflow):

    def __init__(self):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)

    def action(self, extra=None):
        self.build_software()
        return False

    """ PRIVATE """

    def build_software(self):
        # 1500s prompt timeout because the slowest project in the rotation
        # (neovim's CMake/ninja Release build) routinely takes 10-20 min on
        # m1.small. The default 180s gives up partway through and the retry
        # loop (max 3 attempts) burns the whole 30-min stress budget rebuilding
        # the same target instead of finishing once. With 1500s the build
        # completes in a single attempt.
        shell = HumanTyperShell(live_echo=True, prompt_timeout=1500.0)
        try:
            # for testing a particular software build.
            # chosen_projects = [ software_projects[10] ]
            chosen_projects = random.sample(
                software_projects, k=random.randint(1, 2))
            for task_group in chosen_projects:
                run_shell_commands_with_checks(
                    shell, task_group, step_logger=self)
        finally:
            shell.close()


if __name__ == "__main__":

    BuildSoftware().action()
