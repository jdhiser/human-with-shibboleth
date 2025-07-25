import random
import re
from ..utility.human_typer import HumanTyperShell
from ..utility.shell_interact import run_shell_commands_with_checks
from ..utility.metric_workflow import MetricWorkflow


WORKFLOW_NAME = 'BuildSoftware'
WORKFLOW_DESCRIPTION = 'Pick a random piece of software, download it, install prereqs, and build the software'

# Define basic success check using regex


def basic_success(pattern): return lambda task, output, fail_count: (
    "success"
    if re.search(pattern, output)
    else ("retry" if fail_count < 2 else "fail")
)


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
software_projects = cmds([
    [
        ("rm -rf htop*", r".*"),
        ("git clone https://github.com/htop-dev/htop.git", r"Cloning into"),
        ("cd htop", r".*"),
        ("./autogen.sh", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"gcc .* -o htop "),
        ("./htop --help", r"-no-color"),
    ],
    [
        ("rm -rf jq*", r".*"),
        ("git clone https://github.com/jqlang/jq.git", r"Cloning into"),
        ("cd jq", r".*"),
        ("git submodule update --init", r"Submodule|Checking out files"),
        ("autoreconf -fi", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"GEN +src/version\.h"),
        ("./jq --help", r"jq - commandline JSON processor"),
    ],
    [
        ("rm -rf tmux*", r".*"),
        ("git clone https://github.com/tmux/tmux.git", r"Cloning into"),
        ("cd tmux", r".*"),
        ("sh autogen.sh", r"configure"),
        ("./configure", r"config.status"),
        ("make -j", r"tmux"),
        ("./tmux -V", r"tmux"),
    ],
    [
        ("rm -rf micro*", r".*"),
        ("git clone https://github.com/zyedidia/micro.git", r"Cloning into"),
        ("cd micro", r".*"),
        ("make ", r"go build"),
        ("./micro --help", r"Usage: micro"),
    ],
    [
        ("rm -rf neovim*", r".*"),
        ("git clone https://github.com/neovim/neovim.git", r"Cloning into"),
        ("cd neovim", r".*"),
        ("make CMAKE_BUILD_TYPE=Release -j", r"Generating doc/tags"),
        ("./build/bin/nvim --version", r"NVIM"),
    ],
    [
        ("rm -rf wget*", r".*"),
        ("mkdir wget", r".*"),
        ("cd wget", r".*"),
        ("wget https://ftp.gnu.org/gnu/wget/wget-1.21.4.tar.gz", r"Saving to"),
        ("tar xf wget-1.21.4.tar.gz", r".*"),
        ("cd wget-1.21.4", r".*"),
        ("./configure", r"config.status"),
        ("make -j", r"Built target|make\[.*\]"),
        ("src/wget --help", tarball_check_contains("Usage: wget")),
    ],
    [
        ("rm -rf man-db*", r".*"),
        ("wget https://download.savannah.gnu.org/releases/man-db/man-db-2.12.0.tar.xz", r"Saving to"),
        ("tar xf man-db-2.12.0.tar.xz", r".*"),
        ("cd man-db-2.12.0", r".*"),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./src/man --help", tarball_check_contains("Usage: man")),
    ],
    [
        ("rm -rf xz*", r".*"),
        ("curl -LO https://tukaani.org/xz/xz-5.4.5.tar.gz",
         r"Average Speed   Time    Time     Time  Current"),
        ("tar xf xz-5.4.5.tar.gz", r".*"),
        ("cd xz-5.4.5", r".*"),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./src/xz/xz --help", tarball_check_contains("XZ Utils home page")),
    ],
    [
        ("rm -rf ncurses*", r".*"),
        ("wget https://ftp.gnu.org/pub/gnu/ncurses/ncurses-6.4.tar.gz", r"Saving to"),
        ("tar xf ncurses-6.4.tar.gz", r".*"),
        ("cd ncurses-6.4", r".*"),
        ("./configure", r"config.status"),
        ("make -j$(nproc)", r"make\[.*\]|CC"),
        ("./progs/tput --help", tarball_check_contains("Usage")),
    ],
    [
        ("rm -rf sbase*", r".*"),
        ("git clone git://git.suckless.org/sbase", r"Cloning into"),
        ("cd sbase", r".*"),
        ("make -j", r"c99"),
        ("./ls --help || true", r"usage|Usage|invalid option"),
    ],
    [
        ("rm -rf zutils*", r".*"),
        ("wget https://download.savannah.gnu.org/releases/zutils/zutils-1.11.tar.lz", r"Saving to"),
        ("tar --lzip -xf zutils-1.11.tar.lz", r".*"),
        ("cd zutils-1.11", r".*"),
        ("./configure", r"config.status"),
        ("make -j", r"-o zcat"),
        ("./zcat --help", tarball_check_contains("Usage: zcat")),
    ],
    [
        ("rm -rf bash*", r".*"),
        ("wget https://ftp.gnu.org/gnu/bash/bash-5.2.15.tar.gz", r"Saving to"),
        ("tar xf bash-5.2.15.tar.gz", r".*"),
        ("cd bash-5.2.15", r".*"),
        ("./configure", r"config.status"),
        ("make -j", r"make\[.*\]|CC"),
        ("./bash --version", tarball_check_contains("GNU bash")),
    ]
])


def load():
    return BuildSoftware()


class BuildSoftware(MetricWorkflow):

    def __init__(self):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)

    def action(self, extra=None):
        self.build_software()

    """ PRIVATE """

    def build_software(self):
        shell = HumanTyperShell(live_echo=True, prompt_timeout=180.0)
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
