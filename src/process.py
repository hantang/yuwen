"""
md文件处理
"""

import argparse
import difflib
import logging
import re
import shutil
from io import StringIO
from pathlib import Path
from textwrap import dedent

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

PDF_DIR = "pdf"
TEXT_DIR = "text"
RAW_DIR = "raw"
TOC_NAME = "toc.tsv"


def extract_front_matter(md_text: str):
    """
    从 Markdown 内容中提取 Front Matter
    支持 --- xxx --- 或 --- xxx ... 格式
    """
    # 匹配 Front Matter（支持 --- 开始，--- 或 ... 结束）
    pattern = r"^-{3}\s*\n(.*?)\n(?:-{3}|\.{3})\s*$"
    match = re.search(pattern, md_text, re.DOTALL | re.MULTILINE)
    if match:
        yaml_content = match.group(1)
        yaml = YAML()
        try:
            front_matter = yaml.load(yaml_content)
            # 提取剩余的 Markdown 内容
            remaining_content = md_text[match.end() :].lstrip("\n")
            return front_matter, remaining_content
        except Exception as e:
            logging.error(f"YAML 解析错误: {e}")
            return {}, md_text
    else:
        # 没有 Front Matter
        return {}, md_text


def create_front_matter(front_matter_data: dict) -> str:
    """创建 Markdown Front Matter 字符串"""
    if not front_matter_data:
        return ""

    yaml = YAML()
    yaml.explicit_start = True
    # yaml.explicit_end = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    string_stream = StringIO()
    yaml.dump(front_matter_data, string_stream)
    text = string_stream.getvalue() + "---\n"
    return text


def update_mkdocs_nav(mkdocs_config: str, nav: dict) -> None:
    """创建 Markdown Front Matter 字符串"""
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    if Path(mkdocs_config).exists():
        logging.info(f"读取 {mkdocs_config}")
        with open(mkdocs_config, encoding="utf-8") as f:
            config = yaml.load(f)
    else:
        config = {}

    if "nav" in config:   # 允许手动定义的
        raw_nav = config["nav"]
        config["nav"] = raw_nav[:1] + nav + raw_nav[1:]
    else:
        config["nav"] = nav
    logging.info(f"保存到 {mkdocs_config}")
    with open(mkdocs_config, "w", encoding="utf-8") as f:
        yaml.dump(config, f)


def md_to_text(md_text: str) -> str:
    """简化markdown为一般文本"""
    text = md_text
    # 删除front matter
    # text = re.sub(r"^---\n.+?\n---\n", "", text, flags=re.DOTALL | re.MULTILINE)

    # 删除注释
    text = re.sub(r"<!--.+?-->", "", text, flags=re.DOTALL | re.MULTILINE)
    # 删除html
    text = re.sub(r"<[^>]+?>", "", text, flags=re.DOTALL)
    # 删除脚注
    text = re.sub(r"(?<=\n)\[\^[^\]]+\]:\s.*\n(\s{4}\S.*\n)*", r"\n", text)

    # 删除一般性markdown部分
    text = re.sub(r"(^|\n)#{1,6}\s*", r"\1", text)  # 标题
    text = re.sub(r"\[\^[^\]]+\]", "", text)  # 脚注
    text = re.sub(r"(?<![*_])[*_]{1,3}(?![*_])", "", text)  # 加粗、斜体
    text = re.sub(r"\n[\-*_]{3,}\n", "\n", text)  # 分割线
    text = re.sub(r"(?<=\n)(\s{4})*[\-*+]\s+", "", text)  # 列表
    text = re.sub(r"(?<=\n)(> *)+ +", "", text)  # 引用
    text = re.sub(r"(?<=\n)(> *)+\n", "\n", text)  # 引用

    # 代码块、图片、链接、转义字符 略
    # 分行合并
    cjk = r"[\u4E00-\u9FFF\u3000-\u303F\uFE10–\uFE1F\uFF00-\uFFEF“”‘’…•·]"
    text = re.sub(rf"(?<={cjk})\n(?={cjk})", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip("\n")
    return text


def _indent_text(text: str, indent: int) -> str:
    # 文本整体缩进
    space = " " * indent
    lines = text.splitlines()
    out = "\n".join([space + line for line in lines])
    return out


def create_md_tip(yaml_data, indent=4, expand=False):
    """使用admonition/call-out展示【预习】"""
    yaml_key = None
    for key in ["desc", "tip"]:
        if key not in yaml_data:
            continue
        yaml_key = key
    if not yaml_key:
        return "", yaml_key
    desc = yaml_data.get(yaml_key, "").strip()
    tag = None
    if result := re.findall(r"^\s*\*\*(\S+)\*\*\n", desc):
        tag = result[0]
        desc = re.sub(r"^\s*\*\*(\S+)\*\*\n", "", desc)
    if not desc:
        return "", yaml_key

    desc_text = _indent_text(desc.strip(), indent)
    tag_type = "info"
    if yaml_key == "desc":
        if not tag:
            tag = "预习"
    else:
        if not tag:
            tag = "学习提示"
        tag_type = "tip"
    expand_tag = "!!!" if expand else "???"
    out = f'{expand_tag} {tag_type} "{tag}"\n\n{desc_text}'
    return dedent(out), yaml_key


def create_md_tabs(raw_text, book_text, raw_title, book_title, indent=4):
    """原文和课文 tab页"""
    texts = [raw_text, book_text]
    titles = [raw_title, book_title]
    out = []
    for text, title in zip(texts, titles):
        if not text.strip():
            continue
        text2 = _indent_text(text.strip(), indent)
        result = f'=== "{title}"\n\n{text2}'
        out.append(dedent(result))

    return "\n\n".join(out)


def _get_icon(index: int, level: int = 0) -> str:
    """
    index页面添加icon
    :material-numeric-1-box: unit
    :material-numeric-9-box-multiple:
    :material-dice-4:
    """
    icon = "material/atom"
    if level > 0:  # 年级+上下册
        if 1 <= index <= 9:
            plus = "" if level == 1 else "-outline"
            icon = f"material/numeric-{index}-box-multiple{plus}"
        elif 10 <= index <= 12:
            v = (index - 10) * 3 + level
            if 1 <= v <= 9:
                icon = f"material/dice-{v}"
    else:
        # 单元
        if 1 <= index <= 9:
            icon = f"material/numeric-{index}-box"
    return icon



def update_index_text(text_file: Path):
    """
    unit/index.md 增加换行符，避免第一个段落被css影响
    """
    dir_name = text_file.parent.name
    index, level = get_index_level(dir_name)
    icon = _get_icon(index, level)
    with open(text_file, encoding="utf-8") as f:
        text = f.read()
    meta, md_text = extract_front_matter(text)
    meta["icon"] = icon

    desc = ""
    desc, key = create_md_tip(meta, expand=True)
    if desc and key:
        del meta[key]
        if desc:
            desc = f"\n{desc}\n"

    if re.findall(r"^\S+\n\S|^\S{40,}", md_text.strip()):  # 开头是段落或者太长的行（可能非标题）
        md_text = f"\n___\n\n{md_text}"
    fm = create_front_matter(meta)
    text = "\n".join([fm, desc, md_text])
    return text


def tsv_to_md(toc_file, sep="\t"):
    # TODO 课文添加链接
    table = []
    with open(toc_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            cells = line.split(sep)
            line = "| {} |".format(" | ".join(cells))
            table.append(line)
            if len(table) == 1:
                sep_line = "| {} |".format(" | ".join(["---"] * len(cells)))
                table.append(sep_line)
    return "\n".join(table)


def create_book_text(book_name: str, idx_file: Path, toc_file: Path) -> str:
    index_text = ""
    if idx_file.exists():
        with open(idx_file, encoding="utf-8") as f:
            index_text = f.read()

    toc_table = ""
    if toc_file.exists():
        logging.info(f"Read toc = {toc_file}")
        toc_table = tsv_to_md(toc_file)

    index, level = get_index_level(book_name)
    icon = _get_icon(index, level)
    meta = {"title": book_name, "icon": icon}  # "hide": ["toc"]

    if index_text:
        md_text = index_text.replace("<!-- 目录 -->", toc_table)
    else:
        md_text = f"## 目录\n\n{toc_table}" if toc_table else ""

    fm = create_front_matter(meta)
    text = "\n".join([fm, md_text])
    return text


def update_file_text(text_file):
    """更新课文，显示预习"""
    with open(text_file, encoding="utf-8") as f:
        text = f.read()
    meta, md_text = extract_front_matter(text)
    desc = ""
    desc, key = create_md_tip(meta)
    if desc and key:
        del meta[key]
        if desc:
            desc = f"\n{desc}\n"

    fm = create_front_matter(meta)

    # 角落注释内容加粗
    md_text = re.sub(r"(\]:\s+)(〔[^〕]+?〕)", r"\1**\2** ", md_text)
    out = "\n".join([fm, desc, md_text])
    return out


def _compute_diff(raw_text, book_text, fromfile, tofile):
    """计算两个文件diff，待优化，获得最小变更统计"""
    t1, t2 = raw_text.splitlines(), book_text.splitlines()
    diff = difflib.unified_diff(t1, t2, fromfile=fromfile, tofile=tofile, lineterm="")
    diff_text = "\n".join(diff)
    return diff_text


def concat_diff_texts(raw_file, text_file, file_dir, docs_dir):
    """生成原文和课文"""
    pdf_data = None
    with open(raw_file, encoding="utf-8") as f:
        text = f.read()
        raw_meta, md_text = extract_front_matter(text)
        raw_text = md_to_text(md_text)
        pdf_data = raw_meta.get("pdf")

    with open(text_file, encoding="utf-8") as f:
        text = f.read()
        book_meta, md_text = extract_front_matter(text)
        book_text = md_to_text(md_text)

    title = book_meta["title"]
    raw_title = raw_meta.get("title", title)
    raw_title2 = f"【原文】{raw_title}"
    book_title = f"【课文】{title}"

    tab_text = create_md_tabs(raw_text, book_text, raw_title2, book_title)
    tab_text = f"## 内容\n\n{tab_text}"

    pdf_text = ""
    if pdf_data:
        pdf_text_list = ["## 原文"]
        pdf_list = []
        if isinstance(pdf_data, str):
            pdf_list = [pdf_data]
        else:
            pdf_list = pdf_data
        for pdf_name in pdf_list:
            pdf_file = Path(file_dir, PDF_DIR, pdf_name)
            if pdf_file.exists():
                save_pdf_file = Path(docs_dir, PDF_DIR, pdf_name)
                mkdir(save_pdf_file.parent)
                shutil.copy(pdf_file, save_pdf_file)
                pdf_path = save_pdf_file.relative_to(docs_dir).as_posix()
                pdf_md = f'![{pdf_name}]({pdf_path}){{ type=application/pdf }}'
                if len(pdf_list) > 1:
                    subtitle = pdf_name.split("/")[-1].split(".")[0].split(" - ", 1)[-1]
                    pdf_md = f"### {subtitle}\n\n{pdf_md}"
                pdf_text_list.append(pdf_md)
        pdf_text = "\n\n".join(pdf_text_list)

    tab_meta = {
        "title": f"{title}（原文/课文）",
        "author": book_meta.get("author"),
    }
    tab_fm = create_front_matter(tab_meta)
    tab_out = "\n\n".join([tab_fm, pdf_text, tab_text])

    diff_out = ""
    if raw_text.strip():
        diff_text = _compute_diff(raw_text, book_text, fromfile=raw_title, tofile=title)
        diff_meta = {
            "title": f"{title}（课文改动）",
            "author": book_meta.get("author", ""),
            "template": "diff.html",
            "hide": ["toc"],
            "diff": LiteralScalarString(diff_text),  # 多行字符串格式
        }
        diff_out = create_front_matter(diff_meta)
    return tab_out, diff_out


def mkdir(dir_path: Path):
    if not dir_path.exists():
        dir_path.mkdir(parents=True)


def save_text(save_file, text, encoding="utf-8"):
    text = text.lstrip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.rstrip(" \n")
    with open(save_file, "w", encoding=encoding) as f:
        f.write(text + "\n")


def get_file_dict(raw_dir: Path, book_name: str) -> dict:
    # 课本 + 单元 + 课文名区分
    raw_dict = {}
    if not raw_dir.exists():
        return raw_dict

    raw_files = sorted(raw_dir.rglob("*.md"))
    for file in raw_files:
        unit = file.relative_to(raw_dir).parts[0]
        name = file.stem
        raw_dict[(book_name, unit, name)] = file
    assert len(raw_dict) == len(raw_files)
    return raw_dict


def get_index_level(name):
    # 计算年级和分册
    nums = "一二三四五六七八九"
    group = "上中下"
    if "单元" in name:
        result = re.findall(rf"第([{nums}])单元", name)
        unit = nums.index(result[0]) + 1 if result else 99
        return unit, 0
    if "古诗词诵读" in name:
        return 99, 0
    if "册" in name:
        grade = 99
        if "选择性必修" in name:
            grade = 11
        elif "必修" in name:
            grade = 10
        else:
            if result := re.findall(rf"([{nums}])年级", name):
                grade = nums.index(result[0]) + 1

        result = re.findall(rf"年级([{group}])册|[初高]中.*([{group}])", name)
        result2 = [max(v) for v in result if v]
        level = 0
        if result2:
            level = group.index(result2[0]) + 1
        return grade, level
    return 0, 0

def get_unit_index(unit_name):
    nums = "一二三四五六七八九"
    result = re.findall(rf"(第[{nums}])单元", unit_name)
    return nums.index(result[0]) + 1 if result else 99


def build_tree(file_dict):
    tree = {"_files": [], "_dirs": {}}
    for path_str, (order, title) in file_dict.items():
        path = Path(path_str)
        parts = path.parts
        if not parts[-1].endswith(".md"):  # 仅处理文件
            continue
        cur = tree
        for p in parts[:-1]:  # 目录层级
            cur = cur["_dirs"].setdefault(p, {"_files": [], "_dirs": {}})
        item = {"path": path_str, "order": order, "title": title}
        cur["_files"].append(item)
    return tree


def sort_items(files, dirs):
    """排序：文件和目录都用 order 排序"""

    def key_fn(item):
        if isinstance(item, dict):  # 文件
            return item["order"]
        else:  # 目录 (name, dict)
            # 用目录下 index.md 的 order，如果没有则用名字
            d = item[1]
            if d["_files"]:
                return min(f["order"] for f in d["_files"])
            return item[0]

    return sorted(files + dirs, key=key_fn)


def tree_to_nav(tree: dict) -> list:
    nav = []
    files = tree["_files"]
    dirs = list(tree["_dirs"].items())
    for item in sort_items(files, dirs):
        if isinstance(item, dict):  # 文件
            nav.append(item["path"])
        else:  # 目录
            name, subtree = item
            children = tree_to_nav(subtree)
            # 如果目录下有 index 文件，取它的标题
            idx = [f for f in subtree["_files"] if "-" in f["order"] and "index.md" in f["path"]]
            if idx:
                nav.append({idx[0]["title"]: children})
            else:
                nav.append({name: children})
    return nav


def create_nav(nav_dict, mkdocs_config):
    """
    [(file_path, key)]
    """
    nav_levels = ["小学低段", "小学高段", "初中", "高中", "其他"]

    tree = build_tree(nav_dict)
    nav = tree_to_nav(tree)
    out = []
    nav_dict = {g: [] for g in nav_levels}
    for item in nav:  # 新增一层
        # assert len(item) == 1
        for k, v in item.items():
            grade, _ = get_index_level(k)
            nav_group = nav_levels[min((grade - 1) // 3, 4)]
            nav_dict[nav_group].append({k: v})

    for nav_group in nav_levels:
        if nav_dict[nav_group]:
            out.append({nav_group: nav_dict[nav_group]})

    update_mkdocs_nav(mkdocs_config, out)


def create_docs(resource_dir: str, docs_dir: str):
    """
    text_dir 课文
    raw_dir 原文
    save_dir 保存文档

    book/unitX/
        - index.md
        - 课文1/
            - index.md -> 课文原文
            - text.md -> tab展示原文和课文
            - diff.md -> diff.html模板展示
        - 课文2/
            - index.md
            - 篇章1/
                - index.md
                - ...
    """
    resource_path = Path(resource_dir)
    if not resource_path.exists():
        return
    directories = [d for d in resource_path.iterdir() if d.is_dir()]
    logging.info(f"dirs = {len(directories)}")

    nav_dict = {}
    for dir_path in directories:
        book_name = dir_path.name
        if book_name.startswith("."):
            continue

        toc_file = Path(dir_path, TOC_NAME)
        text_dir = Path(dir_path, TEXT_DIR)
        raw_dir = Path(dir_path, RAW_DIR)
        text_files = sorted(text_dir.rglob("*.md"))
        save_dir = Path(docs_dir, book_name)
        if save_dir.exists():
            logging.info("清除旧文档")
            shutil.rmtree(save_dir)

        logging.info(f"正在处理 {book_name}, 文件共 {len(text_files)}")

        if not toc_file.exists():
            logging.warning(f"忽略无TOC目录 = {dir_path}")
            continue
        raw_dict = get_file_dict(raw_dir, book_name)

        # 创建index.md
        idx_file = Path(dir_path, "index.md")
        save_file = Path(save_dir, "index.md")
        text = create_book_text(book_name, idx_file, toc_file)
        mkdir(save_dir)
        save_text(save_file, text)
        index, level = get_index_level(book_name)
        book_order = f"{index:02d}_{level}"
        nav_dict[save_file.relative_to(docs_dir).as_posix()] = (book_order, book_name)

        for file in text_files:
            file_path = file.relative_to(text_dir)
            unit_name = file_path.parts[0]
            key = (book_name, unit_name, file_path.stem)
            logging.debug(f"Process = {key}")

            if file_path.as_posix() == "index.md":
                continue

            is_index_file = file.name == "index.md"
            if is_index_file:
                file_path2 = file_path
                text = update_index_text(file)
            else:
                file_path2 = Path(file_path.with_suffix(""), "index.md")
                text = update_file_text(file)

            save_file = Path(docs_dir, book_name, file_path2)
            mkdir(save_file.parent)
            save_text(save_file, text)

            unit_index, _ = get_index_level(file_path2.parts[0])
            meta, _ = extract_front_matter(text)
            order = f"{book_order}_{unit_index}"
            title = meta.get("title", save_file.parent.name)
            if "index" in meta:
                index, level = str(meta["index"]), meta["unit"]
                page = str(meta["page"]).split("-", maxsplit=1)[0]
                if page.isdigit():
                    page = f"{int(page):03d}"
                else:
                    page = "999"
                order = f"{order}_{page}_{level}"
                if index.isdigit() and 0 < int(index) < 99:
                    title = f"{int(index):02d} {title}"

            nav_dict[save_file.relative_to(docs_dir).as_posix()] = (order, title)

            raw_file = raw_dict.get(key)
            if not is_index_file and raw_file:
                save_dir = save_file.parent
                raw_text, diff_text = concat_diff_texts(raw_file, file, dir_path, docs_dir)

                save_text_file = Path(save_dir, "原文.md")  # 原文 + 课文
                save_text(save_text_file, raw_text)
                nav_dict[save_text_file.relative_to(docs_dir).as_posix()] = (order + "y", title)

                if diff_text:
                    save_diff_file = Path(save_dir, "改动.md")  # 修改统计
                    save_text(save_diff_file, diff_text)
                    nav_dict[save_diff_file.relative_to(docs_dir).as_posix()] = (order + "z", title)

                images = []
                raw_image_dir = Path(raw_file.parent, "images")
                for suffix in ['jpg', 'jpeg', 'png']:
                    images += sorted(raw_image_dir.glob(f"{raw_file.stem}-*.{suffix}"))
                if images:
                    logging.info(f"图片({raw_file}) = {len(images)}")
                    save_image_dir = Path(save_dir, "images")
                    if not save_image_dir.exists():
                        save_image_dir.mkdir(parents=True)
                    for image_file in images:
                        save_image_file = Path(save_image_dir, image_file.name)
                        shutil.copy(image_file, save_image_file)


    # update index.md
    index_file = Path(resource_dir, "index.md")
    if not index_file.exists():
        index_file = Path(resource_dir, "README.md")
    if index_file.exists():
        doc_file = Path(docs_dir, "index.md")
        # shutil.copy(index_file, doc_file)
        with open(index_file, encoding="utf-8") as f:
            text = f.read()
        meta_fm = create_front_matter({"icon": "material/home"})
        text = "\n\n".join([meta_fm, text])
        save_text(doc_file, text)

    # 更新侧边栏导航
    logging.info("更新导航")
    mkdocs_config = Path(docs_dir).parent / "mkdocs.yml"
    create_nav(nav_dict, mkdocs_config)


if __name__ == "__main__":
    fmt = "%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, default="resources", help="原始文档目录")
    parser.add_argument("-o", "--output", type=str, default="docs", help="网站文档目录")
    args = parser.parse_args()

    logging.info(f"args = {args}")
    create_docs(args.input, args.output)
