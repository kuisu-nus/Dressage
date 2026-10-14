#!/bin/bash
# auto_build_swegym.sh

IMAGES_FILE="data/swegym-images.txt"
MAPPING_FILE="data/e2b-template-map.json"  # 用于记录最终映射

echo "{" > $MAPPING_FILE

while IFS= read -r IMAGE || [ -n "$IMAGE" ]; do
  # 跳过空行
  [[ -z "$IMAGE" ]] && continue

  # 生成唯一的 template name，例如：e2b-swegym-<instance-id>
  # 从 image 名中提取 instance id，如 xingyaoww/sweb.eval.x86_64.dask_s_dask-9349 -> dask_s_dask-9349
  INSTANCE_ID=$(echo "$IMAGE" | sed 's|.*sweb.eval.x86_64.||')
  TEMPLATE_NAME="e2b-swegym-${INSTANCE_ID}"

  echo ">>> Building template: $TEMPLATE_NAME from $IMAGE"

  export TASK_IMAGE="$IMAGE"
  export TEMPLATE_NAME="$TEMPLATE_NAME"

  # 执行 build
  python3 examples/data/swegym/prepare_swegym_e2b.py build
  if [ $? -ne 0 ]; then
    echo "!!! Build failed for $IMAGE, skipping smoke test." >&2
    continue
  fi

  # 执行 smoke test
  python3 examples/data/swegym/prepare_swegym_e2b.py smoke
  if [ $? -ne 0 ]; then
    echo "!!! Smoke test failed for $TEMPLATE_NAME" >&2
  fi

  # 记录映射
  echo "  \"$IMAGE\": \"$TEMPLATE_NAME\"," >> $MAPPING_FILE

done < "$IMAGES_FILE"

echo "}" >> $MAPPING_FILE
echo "Mapping written to $MAPPING_FILE"