# Task ID: 7

**Title:** AntV G6 图谱可视化 (2D/3D) + 邻居展开 + 路径查询

**Status:** pending

**Dependencies:** 5

**Priority:** high

**Description:** 基于 AntV G6 实现 2D/3D 知识图谱可视化。功能：双模式切换（2D浅色主题/3D深色主题）、6种布局算法（层次化/力导向/径向/圆形/网格/同心圆）、图内节点搜索与定位、深度滑块控制展开1-5层、右侧280px详情滑出面板（显示节点属性+关联关系）、工具栏（缩放/适应画布/布局切换/导出）、全屏模式、底部状态栏（节点/边统计）、Tab切换实体图谱/结构图谱。

**Details:**

API对接: GET graph/stats, GET graph/knowledge, GET graph/neighbors/{obj_type}/{obj_id}, POST graph/path, POST graph/traverse。详情面板响应式: <1200px→240px, <900px→浮动面板。

**Test Strategy:**

No test strategy provided.
