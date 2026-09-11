# Prerequisites

For the generic JupyterLab Flinc Agent, installation, compatibility, and the
Audit/Repeat workflow, see [FLINC_AGENT_SETUP.md](FLINC_AGENT_SETUP.md).
Agent source and packaging are in [flinc-agent/](flinc-agent/).

For the AWS distributed replay changes on `FLINC-NASA-DEMO_SEP_26`, see
[the branch README](README.FLINC-NASA-DEMO_SEP_26.md).

* Python 3.x with headers and compiler
* pip >= 20.x
* glibc>=2.17

# Reproducible Notebook Containers using Application Virtualization

To install and use FLINC in your Jupyter environment, follow the steps 
below.

1. After extracting the flinc directory, `cd` into it.
2. Find the path of the kernel you wish to audit using this command:

   `jupyter kernelspec list`
   
3. Execute install.sh from the command line:
   
   `./install.sh <user kernel path>`
   
   `<user kernel path>` is the path of the kernel that will execute your notebook code.

4. The script registers the Audit and Repeat kernels. Sciunit must already be
installed and working in the selected Linux environment.
   You may confirm the kernel installations by running:
   
   `jupyter kernelspec list`

   
5. Select the audit kernel from within the notebook and execute your notebook 
code. After execution completes, select 'No Kernel' from the list or shutdown the kernel and wait 30 seconds to 1 minute to complete the auditing.
6. Repeat your notebook code on the same or different machine by selecting 
the repeat kernel.
7. After using the repeat kernel, select No Kernel again to finish.
8. Sciunit will store your notebook as an executable which you can 
view using:

   `sciunit list`

   By running the above command, you can see information about the executable(s) including their corresponding IDs (e.g., `e1`, `e2`, etc.). 

9. To view the dependencies to run the notebook associated with execution ID `e1`, you need to run the following command:

   `sciunit export e1`

   It will create a file named `e1-requirements.txt` in the notebook location to list all the dependencies.

**NOTES**
1. The installer can be rerun. It preserves existing captures and the installed
   Repeat execution selection. Use the original Python kernelspec as input.
2. No existing file should be deleted or modified in the Flinc directory.
3. Run one notebook in a Sciunit project with the audit and repeat kernels. If you have multiple notebooks to audit, create separate Sciunit projects for each notebook.
4. If you run your code using the audit kernel on machine #1, you can repeat it using the repeat kernel on machine #2. To do this, first execute your code using audit kernel, and then run 'sciunit copy' to obtain a unique code. Take that code and run `sciunit open <code>`. This transfers the contents of the notebook container to machine #2 from machine #1.
