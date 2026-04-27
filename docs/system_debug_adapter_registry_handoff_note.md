# System Debug Adapter Registry Handoff Note

日期：2026-04-27

## 1. 本轮交付

本轮在只读 `system_debug_control_plane` 上补了 adapter registry。

新增能力：

- 记录跨链连接语义；
- 检查 source artifact 是否存在；
- 检查 required fields；
- 根据 missing field strategy 给出 block / warn / degrade / manual_fill 判断；
- 在总报告中展示 inbound / outbound adapters；
- 单独列出 explicit / inferred / manual_only 连接；
- 标记 manual bridge required；
- 标记 registered-only 链不应被误判为 ready。

## 2. 新增文件

代码：

- `tools/system_debug_adapter_registry.py`
- `tools/system_debug_adapter_resolution.py`

文档：

- `docs/system_debug_adapter_registry_contract.md`
- `docs/system_debug_adapter_registry_handoff_note.md`

测试：

- `tests/test_system_debug_adapter_registry.py`

修改：

- `tools/system_debug_control_plane.py`
- `tools/system_debug_report.py`

## 3. 新增输出

控制台运行后新增：

- `system_debug_adapter_registry.json`

同时增强：

- `system_debug_report.json`
- `system_debug_report.md`

## 4. 为什么这是当前最小补刀

当前总控台已经能发现文件，但发现文件还不等于知道怎么连接。

adapter registry 正好补中间层：

```text
artifact index
-> adapter registry
-> adapter resolution
-> system debug report
```

这一步仍然是只读的，但它让总控台能回答：

- 哪个 artifact 能喂给哪条链；
- 这个连接是 explicit、inferred 还是 manual_only；
- 缺哪些 required fields；
- 缺字段时应 block、warn、degrade 还是 manual_fill；
- 哪些链只是登记，不能自动接。

## 5. 为什么现在不做 master execution plane

现在不应做自动总执行器，原因：

1. 多条链仍是人工驱动或 manual-only；
2. 生题链、难度链、distill workbench 的 durable artifact 形态尚未完全统一；
3. 材料清洗/选段链仍是 Level 0；
4. source seed 不能被当作 verified source；
5. draft 不能被自动写入 formal config；
6. adapter 缺字段时需要人审和降级策略，而不是自动继续。

如果现在做 master execution plane，会把人工串联误升级为自动编排，风险过高。

## 6. 未来如果真的做自动总控，前置能力

至少还需要：

1. 稳定 artifact schema registry；
2. 每条链统一 run id / correlation id；
3. 链级 execution contract；
4. 链级 dry-run / plan-only 模式；
5. 链级 rollback / cancellation policy；
6. human approval artifact 标准化；
7. 对 manual-only adapter 的正式化或禁用策略；
8. 每条链的安全边界和写回权限矩阵。

在这些完成前，control plane 应继续保持只读。

## 7. 当前最值得继续补的点

下一刀建议：

`adapter field drilldown UI/report`

目标：

- 对每条 adapter 展示 matched artifact；
- 展示 required / optional fields；
- 展示缺字段；
- 展示缺字段降级路径；
- 允许用户标记 manual_fill 说明。

仍然不要自动执行链路。

