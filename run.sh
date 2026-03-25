#!/usr/bin/env bash
set -eu

INPUT_PATH="."
STEP_BUILD=true
STEP_DEP=true
DOCS_PATH="docs"

# 解析命令行参数
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --no-build) STEP_BUILD=false ;;
        --no-dep) STEP_DEP=false ;;
        --input)
            if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
                INPUT_PATH="$2"
                shift
            else
                echo "错误: --input 需要提供一个路径参数"
                exit 1
            fi
            ;;

        *) echo "未知参数: $1"; exit 1 ;;

    esac
    shift
done

# 配置
if [[ -d "$DOCS_PATH" ]]; then
    echo "clean $DOCS_PATH"
    rm -rf "$DOCS_PATH"
fi
mkdir -p "$DOCS_PATH"
cp config/mkdocs-template.yml mkdocs.yml

# 删除不必要的md文件
# find docs -name "*.md" ! -name "index.md" -type f -delete
# find docs -name "*.pdf"  -type f -delete

# 重命名 删除前缀
pushd $INPUT_PATH
for dir in [0-9]*; do
    if [[ -d "$dir" ]]; then
        new_name=$(echo "$dir" | sed -r 's/^[0-9]+[a-z]-//')
        if [[ -n "$new_name" ]] && [[ "$dir" != "$new_name" ]]; then
            echo "rename $dir => $new_name"
            mv "$dir" "$new_name"
        fi
    fi
done
popd

# 生成文档和nav
python src/process.py --input "$INPUT_PATH" --output "$DOCS_PATH"

cp -r config/static "$DOCS_PATH"/
cp -r extra/* "$DOCS_PATH"/

python src/postprocess.py --docs "$DOCS_PATH"

if [[ "$STEP_DEP" == true ]]; then
    pip install .
fi

# 构建静态页面
if [[ "$STEP_BUILD" == true ]]; then
    mkdocs build
    rm -rf site/**/*.{csv,tsv}
fi

echo "Done"
