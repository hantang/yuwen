# 语文探源

![Deploy Site](https://github.com/hantang/cntextbook/actions/workflows/deploy.yml/badge.svg)
![GitHub Commit Badge](https://img.shields.io/github/last-commit/hantang/cntextbook.svg)

## 说明

中小学语文教材课文原文汇集，对比选文修改内容，文本和PDF数据在`docs`分支。

## 完成进度

- 小学低段
    - [ ] 一年级上
    - [x] 一年级下
    - [ ] 二年级上、下
    - [ ] 三年级上、下
- 小学高段
    - [ ] 四年级上
    - [x] 四年级下
    - [ ] 五年级上、下
    - [ ] 六年级上、下
- 初中
    - [x] 七年级上
    - [x] 七年级下
    - [ ] 八年级上、下
    - [ ] 九年级上、下
- 高中
    - [x] 选修上
    - [ ] 选修下
    - [ ] 选择性必修上中下

## 明细

电子教材来自最新版[:link: 国家中小学智慧教育平台-教材](https://basic.smartedu.cn/tchMaterial)，
注意，网站教材内容随时可能有改动，或与实际不一致。
目前以“六三制”课文为参照。历史版本教材有机会再予以收录。
每篇课文OCR转化markdown文档（`text`目录），保持原书结构。

收录原文，包括PDF扫描版（`pdf`目录，命名`作者 - 文章名.pdf`，必要时补充课文名称）
和对应OCR文本版（markdown格式，原文注释酌情收录，`raw目录`，文件名和课文名保持一致）。
原文的版本应优先采用课文中脚注中所选版本的扫描版本，次选同一出版社其他版次；
部分来自报刊的文章，可考虑采用作者的选集本作为代替。

对原文是外文，而采用翻译版本的文章，有条件的也可收录到`more`目录，非英文语言的文章如有优秀的英文参考译本也可列入。

OCR转化的markdown文本，每一行应该和PDF文件保持一致，
跨页的段落应和前页保持连续，脚注应适当后移。
教材课文的脚注应该用`[^页面-编号]`，页面以课文正文页为第一页，编号以字母或数字格式有序组织。

## 相关工具

- [microsoft/markitdown](https://github.com/microsoft/markitdown)
