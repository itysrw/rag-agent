# Day 5 Chunk Size 结构对比

更新时间：2026-07-15（America/New_York）

## 目的与边界

本实验只比较 300、500、800 token 切分配置产生的结构差异，不评价检索质量。
检索相关性、source hit rate 和回答质量需要在后续具备检索与评测链路后验证。

## 可复现设置

- 切分器：`RecursiveCharacterTextSplitter`
- Tokenizer：`tiktoken` 的 `o200k_base`
- 长度单位：token
- 配置：`300/60`、`500/100`、`800/160`，overlap 均为 chunk size 的 20%
- 分隔顺序：段落、换行、中英文句末标点、分号、逗号、空格；无自然边界的超长残段
  使用有界 token 窗口兜底
- `keep_separator="end"`
- 语料：`backend/tests/test_text_splitter.py:representative_text()` 生成的固定公开测试语料；
  共 30 个 Markdown 风格小节，每节包含中文、英文、列表式标点和事务处理描述
- 原文 token 数：1,980

执行入口使用项目的 `split_pages()`，语料作为单个非空页面输入。所有数字均来自本地实际运行。

## 结果

| chunk/overlap | Chunk 数 | 平均 token | 最大 token | Chunk token 总和 | 冗余率估算 | 空 Chunk | 超限 Chunk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 300/60 | 8 | 247.50 | 264 | 1,980 | 0.00% | 0 | 0 |
| 500/100 | 5 | 448.80 | 462 | 2,244 | 13.33% | 0 | 0 |
| 800/160 | 3 | 748.00 | 792 | 2,244 | 13.33% | 0 | 0 |

冗余率估算公式：`(所有 chunk token 总和 - 原文 token 数) / 原文 token 数`。
它用于描述 overlap 带来的结构冗余，不等同于逐 token 重复率；分隔符保留和 tokenizer
在边界处的编码也会影响该数值。300/60 在这份语料中没有产生可测冗余，说明配置了
overlap 并不保证每个自然分隔边界都会出现重复。

## 结构观察

- 三种配置均没有空 Chunk 或超出配置上限的 Chunk。
- chunk size 增大时，这份固定语料产生的 Chunk 数减少、平均 Chunk token 数增加。
- overlap 会保留相邻 Chunk 的部分上下文，因此总 token 数可能高于原文。
- 这些结果不能证明任一配置的检索效果更好；生产默认值 `500/100` 只是 Day 5 的配置基线。
