#!/bin/bash
set -e

if (( $# != 1 ))
then
  echo "Provide the user kernel path as an argument!"
  exit 1
fi

# --- config for the on-the-fly sciunit build -------------------------------
SCIUNIT_REPO_URL="https://github.com/radiant-systems-lab/sciunit.git"
SCIUNIT_REF="master"
PATCH_DIR="$(pwd)/patches"
PATCH_FILES=(
  "${PATCH_DIR}/flinc-sigint.patch"
)

if ! command -v git &> /dev/null
then
    apt-get update
    apt-get install -y git
fi

# step 1: download sciunit from upstream, apply FLINC's patches, build 
# and install it from source
pip install cmake

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

git clone --depth 1 --branch "${SCIUNIT_REF}" "${SCIUNIT_REPO_URL}" "${BUILD_DIR}/sciunit"

pushd "${BUILD_DIR}/sciunit" > /dev/null

for patch_file in "${PATCH_FILES[@]}"
do
  if ! git apply --check "${patch_file}" 2> /dev/null
  then
    echo "ERROR: ${patch_file} no longer applies cleanly to" >&2
    echo "       ${SCIUNIT_REPO_URL}@${SCIUNIT_REF}." >&2
    echo "       Upstream likely changed the patched file -- update the patch by hand and retry." >&2
    exit 1
  fi
  git apply "${patch_file}"
done

pip install .

popd > /dev/null

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

# # step 6: update the repeat kernel
# repeatkernelpath="repeat-kernel/kernel.json"
# add="\\\t\"$(pwd)/repeat-handler.py\","
# sed -i "/argv\": \[/a $add" ${repeatkernelpath}

# step 7: cp repeat handler to sciunit folder to be used in repeat kernel generation
cp repeat-handler.py ~/sciunit/


# step 8: install the repeat kernel
jupyter kernelspec install --user repeat-kernel/
echo "Installed the repeat kernel"

# now just execute the notebook code with the audit and repeat kernels