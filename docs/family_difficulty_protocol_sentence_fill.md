# sentence_fill 难度协议

## 1. 适用范围

本协议只定义 `sentence_fill` 在当前最小闭环中的难度控制口径，用于：

- 难度 target 投影
- prompt/validator 消费
- 生成后实际难度评估
- 与真题 gold 画像做 diff

本轮不追求终局精度，只追求“可比较、可回放、可校准”。

## 2. 四个最小难度轴

### 2.1 `local_binding_complexity`

看空句与前后句之间的局部绑定是否紧、是否必须双向成立。

重点观察：

- 是否必须同时承前启后
- 是否依赖明确锚点、代词回指或局部逻辑闭环
- 错放到相邻位置时是否仍然看起来“勉强能读”

### 2.2 `global_context_dependency`

看正确项是否必须借助更大范围段落语义才能成立，而不是只靠邻句拼接。

重点观察：

- 是否要回看段落主轴
- 是否要结合前文铺垫与后文展开共同判断
- 是否存在“局部像对、全段不对”的读感

### 2.3 `distractor_similarity`

看干扰项与正确项在主题、句法功能、位置适配感上的接近程度。

重点观察：

- 干扰项是否也像“能填进去”
- 错项是否共享主题词、关系词或相近功能
- 错项是否是“真竞争”，而不是一眼假的废项

### 2.4 `blank_function_ambiguity`

看空位功能是否容易混淆，例如“承前”与“承前启后”、“总结”与“结论提升”之间的边界是否模糊。

重点观察：

- function type 是否需要结合全文才能判稳
- 只看邻句时是否容易误判
- 空位承担的是不是复合功能

## 3. easy / medium / hard 画像

### easy

- `local_binding_complexity` 低
- `global_context_dependency` 低
- `distractor_similarity` 低到中低
- `blank_function_ambiguity` 低

典型读感：

- 正确项与前后句关系比较直接
- 主要靠单侧线索或局部线索就能确认
- 干扰项要么位置感弱，要么功能明显不对
- 空位功能边界较清楚

典型场景：

- 开头总领但主题非常直给
- 结尾总结但收束方向明确
- 中间承前或启后关系单一

### medium

- `local_binding_complexity` 中等
- `global_context_dependency` 中等
- `distractor_similarity` 中等
- `blank_function_ambiguity` 中等

典型读感：

- 需要同时看邻句与段落局部结构
- 正确项与至少一个干扰项存在真实竞争
- 功能判断需要稍微分辨“承前 / 启后 / 过渡 / 小结”的差别
- 错项不是离谱错误，而是方向、范围或作用域有偏差

典型场景：

- 中段桥接
- lead_next 与 bridge 接近
- 结尾带总结色彩但还保留推进性

### hard

- `local_binding_complexity` 高
- `global_context_dependency` 高
- `distractor_similarity` 高
- `blank_function_ambiguity` 高

典型读感：

- 必须双向验证，且只看邻句不够
- 要结合整段主轴、话题推进方向或引用对象来判
- 至少两个干扰项具备较强“表面可填感”
- 空位功能容易落在复合区：既回收前文，又启动后文，或既概括又转向

典型场景：

- inserted / mixed 型空位
- reference_summary 依赖明确指代锚点
- bridge / lead_next / summary 边界接近
- 多个干扰项在语义位置上都“像那么回事”

## 4. assessment 口径

本轮 `sentence_fill` 实际难度评估主要看：

- 正确项与前后文的局部贴合读感
- 正确项与干扰项之间的竞争强度
- 指代、回指、总结、转向等功能是否需要更大语境才能判稳

允许使用轻量启发式，但目标是服务“读感判断”，不是替代人工阅读。

## 5. calibration 杠杆

### `question_card`

适合调整：

- 默认 axis center
- slot 默认值
- blank_position / function_type 的默认搭配

### `prompt_assets`

适合调整：

- 对承前启后、全局依赖、干扰项竞争的提示语
- 对正确项必须保留真值来源的强调
- 对干扰项构造方式的约束

### `validator`

适合调整：

- 双向成立检查
- reference anchor 检查
- 位置-功能一致性检查

## 6. 不在本轮范围

- sentence_fill 全子母族全覆盖
- 基于线上反馈自动调参
- 自动改写主配置
- 蒸馏层自动闭环写回
