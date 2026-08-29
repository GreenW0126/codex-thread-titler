# Codex Thread Titler

一个为 Codex 任务生成中文标题候选的本地插件。它在首次回复正文末尾自然附上三个标题选项，并在用户回复 A、B 或 C 后重命名当前任务。

## 解决的问题

当项目中的任务越来越多时，Codex 默认显示的首条消息摘要或过程型标题很难帮助用户快速辨认内容。这个插件优先保留：

- 对话最初的核心对象；
- 用户开启对话的原始意图；
- 真正想判断、获得、改变或避免的问题。

标题会避开“从……寻找……”“从……延伸……”等过程性表达，优先采用具体对象与关键问题、目标或产物的组合。

## 使用方式

新建 Codex 任务并正常发送第一条消息。插件会让 Codex 完整回答原问题，然后在同一条回复末尾附加：

```text
对话标题

A. <标题>
B. <标题>
C. <标题>

请回复 A、B 或 C。
```

回复 A、B 或 C 后，Codex 会应用对应标题。也可以回复“重新生成”获得新候选，或回复“跳过”。

## 工作方式

- `UserPromptSubmit` 在第一条消息提交时注入标题生成要求；
- `Stop` 只读取并保存回答末尾的三个候选，不阻断正文，也不创建额外请求；
- 候选状态保存在 Codex 提供的 `PLUGIN_DATA` 目录；
- 插件不解析不稳定的会话 transcript，也不访问网络。

插件 Hook 首次安装或定义变化后，需要在 Codex 的 `/hooks` 页面中信任并启用 `UserPromptSubmit` 和 `Stop`。

## 项目结构

```text
.codex-plugin/plugin.json                 插件清单
hooks/hooks.json                          Hook 定义
scripts/thread_titler_hook.py             Hook 实现
skills/codex-thread-titler/SKILL.md       手动标题技能
tests/test_thread_titler_hook.py          行为测试
```

## 本地验证

```bash
python3 -m unittest discover -s tests -v
```

如本机包含 Codex 的 `plugin-creator` 技能，还可以运行插件结构验证：

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

## 当前状态

这是正在迭代的个人插件。公开发布前还需要确定许可证，并在 GitHub 仓库地址确定后补充面向其他用户的安装说明。
