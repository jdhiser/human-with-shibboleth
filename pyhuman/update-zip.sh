#!/bin/bash

WORKFLOW_ZIP=/home/jdh8d/umbrellas/castle/uva-cs-auth-workflow-openstack/Downloads/workflows.zip

main()
{
	while IFS= read -r file; 
	do
	    if [ -f "$file" ]; then
		zip -u $WORKFLOW_ZIP "$file"
	    fi
    	done < <(zipinfo -1 $WORKFLOW_ZIP )

}

main $@
