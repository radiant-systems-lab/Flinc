This repository contains the code for the tool **FLINC** which audits and containerizes interactive notebook executions. It is based on the following research paper:
```
R. Ahmad, N. N. Manne and T. Malik, "Reproducible Notebook Containers using Application Virtualization,"
2022 IEEE 18th International Conference on e-Science (e-Science), Salt Lake City, UT, USA, 2022, pp. 1-10,
doi: 10.1109/eScience55777.2022.00015.
```

# Prerequisites
* Python 3.x with headers and compiler
* pip >= 20.x
* glibc>=2.17

# Reproducible Notebook Containers using Application Virtualization

To install and use FLINC in your Jupyter environment, follow the steps 
below.

1. After extracting the *Flinc* directory, `cd` into it.
2. Find the path of the kernel you wish to audit using this command:

   `jupyter kernelspec list`
   
3. Execute `install.sh` from the command line:
   
   `./install.sh <user kernel path>`
   
   `<user kernel path>` is the path of the kernel that will execute your notebook code.

4. The successful execution of the above script will result in the installation of Sciunit, audit kernel, and repeat kernel.
   You may confirm the kernel installations by running:
   
   `jupyter kernelspec list`

   
5. Select the audit kernel from within the notebook and execute your notebook 
code. After execution completes, select **No Kernel** from the list or shutdown the kernel. Wait anywhere from few seconds to few minutes to complete auditing and container creation in the background. Each audit run will create a new Sciunit container in the background.
6. Repeat your notebook code on the same or different machine by selecting the repeat kernel. It will repeat the last audited execution. 
7. After using the repeat kernel, select **No Kernel** again to finish.
8. Sciunit will store your notebook as an executable which you can 
view using:

   `sciunit list`

   By running the above command, you can see information about the executable(s) including their corresponding IDs (e.g., `e1`, `e2`, etc.). 

9. To view the dependencies needed to run the notebook associated with an execution ID, say `e1`, you need to run the following command:

   `sciunit export e1`

   It will create a file named `e1-requirements.txt` in the notebook location to list all the dependencies.

**NOTES**
1. The script `install.sh` must only be executed once to install the audit and repeat kernels.
2. No existing file should be deleted or modified in the *Flinc* directory.
3. Run one notebook in a Sciunit project with the audit and repeat kernels. If you have multiple notebooks to audit, create separate Sciunit projects for each notebook.
4. If you run your code using the audit kernel on machine #1, you can repeat it using the repeat kernel on machine #2. To do this, first execute your code using audit kernel, and then run 'sciunit copy' to obtain a unique code. Take that code and run `sciunit open <code>`. This transfers the contents of the notebook container to machine #2 from machine #1.
