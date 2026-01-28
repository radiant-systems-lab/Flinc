#!/bin/bash

if (( $# != 1 ))
then
  echo "Provide the user kernel path as an argument!"
  exit 1
fi

# step 1: install sciunit from the given executable
# pip install cmake
# pip install sciunit2-0.4.post117.dev203853284.tar.gz
sciunit create -f audit-kernel

# step 2: copy kernel.json file of user kernel
kernelfilepath="$1/kernel.json"
auditkerneldir="audit-kernel"
mkdir -p ${auditkerneldir}
cp ${kernelfilepath} ${auditkerneldir}

# step 3: add script instructions
auditkernelpath="audit-kernel/kernel.json"
add="\\\t\"$(pwd)/handler.py\",\"sciunit\",\"exec\","
# sed -i "/prepend_and_launch.sh\",/a $add" ${auditkernelpath}
sed -i "/argv\": \[/a $add" ${auditkernelpath}

if ! command -v python &> /dev/null
then
    apt-get update
    apt-get install -y python-is-python3
fi

# step 4: update kernel name
sed -i -E "s/(\"display_name\": \")(.+)\",/\1Sciunit Audit(\2)\",/" ${auditkernelpath}

# step 5: install the audit kernel
jupyter kernelspec install --user audit-kernel/
echo "Installed the audit kernel"

# step 6: update the repeat kernel
repeatkernelpath="repeat-kernel/kernel.json"
add="\\\t\"$(pwd)/repeat-handler.py\","
sed -i "/argv\": \[/a $add" ${repeatkernelpath}

# step 7: install the repeat kernel
jupyter kernelspec install --user repeat-kernel/
echo "Installed the repeat kernel"

# now just execute the notebook code with the audit and repeat kernels
