/* 删除中文和中文标点之间的空格*/
(function () {
  // [\u4e00-\u9fff\u3000-\u303f\uff00-\uffef“”‘’]
  const chineseChars = "[\\p{Script=Han}\\u3000-\\u303F\\uFE10–\\uFE1F\\uFF00-\\uFFEF“”‘’…•·]";
  const regex = new RegExp(
    `(?<=${chineseChars})[ \\t]+(?=${chineseChars})|^[ \\t]+|[ \\t]+$`,
    "gu"
  );

  function cleanChineseSpaces(container) {
    function cleanTextNodes(node) {
      if (node.nodeType === Node.TEXT_NODE) {
        node.nodeValue = node.nodeValue.replace(regex, "");
      } else {
        node.childNodes.forEach(cleanTextNodes);
      }
    }
    cleanTextNodes(container);
  }

  // MkDocs Material SPA 事件，每次页面加载都会触发
  document$.subscribe(() => {
    const content = document.querySelector(".md-content");
    if (content) {
      cleanChineseSpaces(content);
    }
  });
})();
