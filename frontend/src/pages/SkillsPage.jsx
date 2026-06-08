import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Tag, Space, Popconfirm,
  Tabs, message, Row, Col, Switch, Tooltip, Badge, Descriptions,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, DownloadOutlined,
  UploadOutlined, CopyOutlined, ThunderboltOutlined, SearchOutlined,
  PlayCircleOutlined, PauseCircleOutlined, ImportOutlined, ApiOutlined,
} from '@ant-design/icons';
import * as skillsApi from '../api/skills';

const CATEGORIES = [
  { value: 'general', label: '通用' },
  { value: 'ingestion', label: '数据摄入' },
  { value: 'ontology', label: '本体管理' },
  { value: 'graphrag', label: 'GraphRAG' },
  { value: 'quality', label: '数据质量' },
  { value: 'knowledge', label: '知识库' },
  { value: 'generated', label: '自动生成' },
  { value: 'imported', label: '导入' },
];


export default function SkillsPage() {
  const [loading, setLoading] = useState(false);
  const [skills, setSkills] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [presets, setPresets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeTab, setActiveTab] = useState('skills');

  // Filters
  const [searchText, setSearchText] = useState('');
  const [filterCategory, setFilterCategory] = useState(null);
  const [filterEnabled, setFilterEnabled] = useState(false);

  // Skill modal
  const [skillModalOpen, setSkillModalOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState(null);
  const [skillForm] = Form.useForm();
  const [skillSaving, setSkillSaving] = useState(false);

  // Import modal
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importSelected, setImportSelected] = useState([]);

  // Generate modal
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [genForm] = Form.useForm();
  const [genSaving, setGenSaving] = useState(false);

  // Upload modal
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadJson, setUploadJson] = useState('');
  const [uploadSaving, setUploadSaving] = useState(false);

  // Detail drawer
  const [detailSkill, setDetailSkill] = useState(null);

  const fetchSkills = useCallback(async (p) => {
    setLoading(true);
    try {
      const pageNum = p || page;
      const params = { page: pageNum, page_size: 50 };
      if (filterCategory) params.category = filterCategory;
      if (searchText) params.search = searchText;
      if (filterEnabled) params.enabled = true;
      const res = await skillsApi.listSkills(params);
      if (res.code === 0) {
        setSkills(res.data.items || []);
        setTotal(res.data.page_info?.total || 0);
      }
    } catch (e) {
      message.error('加载技能列表失败');
    }
    setLoading(false);
  }, [page, filterCategory, searchText, filterEnabled]);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await skillsApi.listPresets();
      if (res.code === 0) setPresets(res.data || []);
    } catch { /* ignore */ }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await skillsApi.listCategories();
      if (res.code === 0) setCategories(res.data || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchSkills(1); }, [fetchSkills]);
  useEffect(() => { fetchPresets(); fetchCategories(); }, [fetchPresets, fetchCategories]);

  // ── Skill CRUD ──────────────────────────────────────────

  const openSkillModal = (skill) => {
    if (skill) {
      setEditingSkill(skill);
      skillForm.setFieldsValue({
        ...skill,
        tags: skill.tags || [],
        schema: skill.schema ? JSON.stringify(skill.schema, null, 2) : '',
      });
    } else {
      setEditingSkill(null);
      skillForm.resetFields();
      skillForm.setFieldsValue({ category: 'general', version: '1.0.0', enabled: true });
    }
    setSkillModalOpen(true);
  };

  const handleSkillSave = async () => {
    const values = await skillForm.validateFields();
    setSkillSaving(true);
    try {
      const payload = {
        name: values.name,
        display_name: values.display_name,
        category: values.category,
        description: values.description,
        tags: values.tags || [],
        author: values.author,
        version: values.version,
        enabled: values.enabled,
        icon: values.icon,
        skill_md: values.skill_md,
        prompt_md: values.prompt_md,
      };
      if (values.schema) {
        try {
          payload.schema = JSON.parse(values.schema);
        } catch {
          message.error('Schema JSON 格式无效');
          setSkillSaving(false);
          return;
        }
      }
      let res;
      if (editingSkill) {
        res = await skillsApi.updateSkill(editingSkill.id, payload);
      } else {
        res = await skillsApi.createSkill(payload);
      }
      if (res.code === 0) {
        message.success(editingSkill ? '技能已更新' : '技能已创建');
        setSkillModalOpen(false);
        fetchSkills(1);
      }
    } finally {
      setSkillSaving(false);
    }
  };

  const handleDeleteSkill = async (id) => {
    const res = await skillsApi.deleteSkill(id);
    if (res.code === 0) {
      message.success('技能已删除');
      fetchSkills(1);
    }
  };

  const handleToggleSkill = async (skill) => {
    const res = skill.enabled
      ? await skillsApi.disableSkill(skill.id)
      : await skillsApi.enableSkill(skill.id);
    if (res.code === 0) {
      message.success(skill.enabled ? '已禁用' : '已启用');
      fetchSkills(page);
    }
  };

  const handleCloneSkill = async (skill) => {
    const newName = `${skill.name}-clone-${Date.now()}`;
    const res = await skillsApi.cloneSkill(skill.id, newName);
    if (res.code === 0) {
      message.success('已克隆');
      fetchSkills(1);
    }
  };

  const handleDownloadSkill = async (skill) => {
    const res = await skillsApi.downloadSkill(skill.id);
    if (res.code === 0) {
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${skill.name}-skill-pack.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('下载中');
    }
  };

  // ── Import presets ──────────────────────────────────────

  const handleImportPresets = async () => {
    if (!importSelected.length) return;
    setImporting(true);
    try {
      const res = await skillsApi.importPresets(importSelected);
      if (res.code === 0) {
        message.success(res.message || '导入完成');
        setImportModalOpen(false);
        setImportSelected([]);
        fetchSkills(1);
      }
    } finally {
      setImporting(false);
    }
  };

  // ── Upload pack ─────────────────────────────────────────

  const handleUploadPack = async () => {
    if (!uploadJson.trim()) return;
    setUploadSaving(true);
    try {
      let pack;
      try {
        pack = JSON.parse(uploadJson);
      } catch {
        message.error('JSON 格式无效');
        setUploadSaving(false);
        return;
      }
      const res = await skillsApi.uploadSkillPack(pack);
      if (res.code === 0) {
        message.success(res.message || '上传成功');
        setUploadModalOpen(false);
        setUploadJson('');
        fetchSkills(1);
      }
    } finally {
      setUploadSaving(false);
    }
  };

  // ── Generate from Action ────────────────────────────────

  const handleGenerateFromAction = async () => {
    const values = await genForm.validateFields();
    setGenSaving(true);
    try {
      const res = await skillsApi.generateFromAction(values.dataset_id, {
        action_name: values.action_name,
        category: values.category || 'generated',
        display_name: values.display_name,
        description: values.description,
      });
      if (res.code === 0) {
        message.success(res.message || '技能已生成');
        setGenModalOpen(false);
        fetchSkills(1);
      }
    } finally {
      setGenSaving(false);
    }
  };

  // ── Table columns ───────────────────────────────────────

  const columns = [
    {
      title: '名称', dataIndex: 'name', width: 160,
      render: (v, r) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => setDetailSkill(r)} style={{ fontWeight: 600 }}>{v}</a>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>{r.display_name}</span>
        </Space>
      ),
    },
    {
      title: '分类', dataIndex: 'category', width: 100,
      render: v => <Tag color="purple">{v}</Tag>,
    },
    {
      title: '标签', dataIndex: 'tags', width: 200,
      render: v => (v || []).slice(0, 3).map(t => <Tag key={t} style={{ marginBottom: 2 }}>{t}</Tag>),
    },
    { title: '版本', dataIndex: 'version', width: 80 },
    {
      title: '来源', dataIndex: 'is_preset', width: 80,
      render: v => v ? <Tag color="blue">预设</Tag> : <Tag>自定义</Tag>,
    },
    {
      title: '状态', dataIndex: 'enabled', width: 70,
      render: v => v ? <Badge status="success" text="启用" /> : <Badge status="default" text="禁用" />,
    },
    {
      title: '更新时间', dataIndex: 'updated_at', width: 160,
      render: v => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'actions', width: 280, fixed: 'right',
      render: (_, r) => (
        <Space size="small">
          <Tooltip title="查看详情"><Button size="small" onClick={() => setDetailSkill(r)} icon={<SearchOutlined />} /></Tooltip>
          <Tooltip title="编辑"><Button size="small" onClick={() => openSkillModal(r)} icon={<EditOutlined />} /></Tooltip>
          <Tooltip title={r.enabled ? '禁用' : '启用'}>
            <Button size="small" onClick={() => handleToggleSkill(r)} icon={r.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />} />
          </Tooltip>
          <Tooltip title="克隆"><Button size="small" onClick={() => handleCloneSkill(r)} icon={<CopyOutlined />} /></Tooltip>
          <Tooltip title="下载技能包"><Button size="small" onClick={() => handleDownloadSkill(r)} icon={<DownloadOutlined />} /></Tooltip>
          <Popconfirm title="确认删除?" onConfirm={() => handleDeleteSkill(r.id)}>
            <Tooltip title="删除"><Button size="small" danger icon={<DeleteOutlined />} /></Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const presetColumns = [
    { title: '名称', dataIndex: 'name', width: 180 },
    { title: '显示名', dataIndex: 'display_name', width: 180 },
    { title: '分类', dataIndex: 'category', width: 100, render: v => <Tag color="purple">{v}</Tag> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '标签', dataIndex: 'tags', width: 180, render: v => (v || []).map(t => <Tag key={t}>{t}</Tag>) },
  ];

  // ── Tab items ───────────────────────────────────────────

  const tabItems = [
    {
      key: 'skills',
      label: `技能列表 (${total})`,
      children: (
        <div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Input
                prefix={<SearchOutlined />}
                placeholder="搜索名称/描述..."
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                onPressEnter={() => { setPage(1); fetchSkills(1); }}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="按分类过滤"
                value={filterCategory}
                onChange={v => { setFilterCategory(v); setPage(1); }}
                allowClear
                style={{ width: '100%' }}
                options={[...categories.map(c => ({ value: c, label: c })), ...CATEGORIES].filter((v, i, a) => a.findIndex(x => x.value === v.value) === i)}
              />
            </Col>
            <Col span={4}>
              <Space>
                <span>仅启用</span>
                <Switch checked={filterEnabled} onChange={v => { setFilterEnabled(v); setPage(1); }} />
              </Space>
            </Col>
            <Col flex="auto" style={{ textAlign: 'right' }}>
              <Space>
                <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>导入预设</Button>
                <Button icon={<UploadOutlined />} onClick={() => setUploadModalOpen(true)}>上传技能包</Button>
                <Button icon={<ApiOutlined />} onClick={() => setGenModalOpen(true)}>从 Action 生成</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => openSkillModal(null)}>新建技能</Button>
              </Space>
            </Col>
          </Row>
          <Table
            columns={columns}
            dataSource={skills}
            rowKey="id"
            loading={loading}
            size="middle"
            pagination={{
              current: page,
              pageSize: 50,
              total,
              onChange: (p) => { setPage(p); fetchSkills(p); },
              showTotal: (t) => `共 ${t} 项`,
            }}
            scroll={{ x: 1200 }}
          />
        </div>
      ),
    },
    {
      key: 'presets',
      label: `预设技能 (${presets.length})`,
      children: (
        <Card loading={loading}>
          <Table
            columns={presetColumns}
            dataSource={presets}
            rowKey="name"
            size="middle"
            rowSelection={{
              selectedRowKeys: importSelected,
              onChange: setImportSelected,
            }}
          />
          {importSelected.length > 0 && (
            <Button
              type="primary"
              icon={<ImportOutlined />}
              style={{ marginTop: 16 }}
              loading={importing}
              onClick={handleImportPresets}
            >
              导入选中的 {importSelected.length} 个预设
            </Button>
          )}
        </Card>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>
        <ThunderboltOutlined style={{ marginRight: 8 }} />
        Skills 管理
      </h1>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      {/* Skill Create/Edit Modal */}
      <Modal
        title={editingSkill ? '编辑技能' : '新建技能'}
        open={skillModalOpen}
        onOk={handleSkillSave}
        onCancel={() => setSkillModalOpen(false)}
        confirmLoading={skillSaving}
        width={800}
        forceRender
      >
        <Form form={skillForm} layout="vertical" initialValues={{ category: 'general', version: '1.0.0', enabled: true }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="Name (标识符)" rules={[{ required: true, pattern: /^[a-z0-9_-]+$/, message: '仅允许小写字母、数字、下划线、连字符' }]}>
                <Input placeholder="my-skill-name" disabled={!!editingSkill} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
                <Input placeholder="我的技能" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="category" label="分类" rules={[{ required: true }]}>
                <Select options={CATEGORIES} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="version" label="版本">
                <Input placeholder="1.0.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="author" label="作者">
                <Input placeholder="作者名" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="tags" label="标签">
                <Select mode="tags" placeholder="输入标签后回车" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="icon" label="图标">
                <Input placeholder="database / build / ..." />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="enabled" label="启用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="skill_md" label="SKILL.md">
            <Input.TextArea rows={6} placeholder="# 技能名称&#10;&#10;## 描述&#10;..." />
          </Form.Item>
          <Form.Item name="prompt_md" label="prompt.md (LLM Prompt)">
            <Input.TextArea rows={6} placeholder="You are a..." />
          </Form.Item>
          <Form.Item name="schema" label="schema.json (JSON)">
            <Input.TextArea rows={6} placeholder='{"inputs": [...], "outputs": [...]}' />
          </Form.Item>
        </Form>
      </Modal>

      {/* Import Presets Modal */}
      <Modal
        title="导入预设技能"
        open={importModalOpen}
        onOk={handleImportPresets}
        onCancel={() => { setImportModalOpen(false); setImportSelected([]); }}
        confirmLoading={importing}
      >
        <p style={{ marginBottom: 12, color: '#64748b' }}>选中要导入的预设技能包。已导入的会自动跳过。</p>
        <Table
          columns={presetColumns}
          dataSource={presets}
          rowKey="name"
          size="small"
          rowSelection={{
            selectedRowKeys: importSelected,
            onChange: setImportSelected,
          }}
          pagination={false}
        />
      </Modal>

      {/* Upload Skill Pack Modal */}
      <Modal
        title="上传技能包"
        open={uploadModalOpen}
        onOk={handleUploadPack}
        onCancel={() => { setUploadModalOpen(false); setUploadJson(''); }}
        confirmLoading={uploadSaving}
        width={700}
      >
        <p style={{ marginBottom: 8, color: '#64748b' }}>粘贴技能包 JSON：</p>
        <Input.TextArea
          rows={16}
          value={uploadJson}
          onChange={e => setUploadJson(e.target.value)}
          placeholder='{"name": "my-skill", "display_name": "...", "category": "...", "files": {"SKILL.md": "...", "prompt.md": "...", "schema.json": {...}}}'
        />
      </Modal>

      {/* Generate from Action Modal */}
      <Modal
        title="从 Action Type 生成技能"
        open={genModalOpen}
        onOk={handleGenerateFromAction}
        onCancel={() => setGenModalOpen(false)}
        confirmLoading={genSaving}
      >
        <Form form={genForm} layout="vertical" initialValues={{ category: 'generated' }}>
          <Form.Item name="dataset_id" label="Dataset ID" rules={[{ required: true }]}>
            <Input placeholder="数据集 ID" />
          </Form.Item>
          <Form.Item name="action_name" label="Action Name" rules={[{ required: true }]}>
            <Input placeholder="动作类型名称" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称（可选）">
            <Input placeholder="留空则使用 Action Type 的 display_name" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select options={CATEGORIES} />
          </Form.Item>
          <Form.Item name="description" label="描述（可选）">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Drawer */}
      <Modal
        title={detailSkill ? `技能详情: ${detailSkill.name}` : ''}
        open={!!detailSkill}
        onCancel={() => setDetailSkill(null)}
        footer={null}
        width={800}
      >
        {detailSkill && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="ID">{detailSkill.id}</Descriptions.Item>
            <Descriptions.Item label="Name">{detailSkill.name}</Descriptions.Item>
            <Descriptions.Item label="显示名">{detailSkill.display_name}</Descriptions.Item>
            <Descriptions.Item label="分类"><Tag color="purple">{detailSkill.category}</Tag></Descriptions.Item>
            <Descriptions.Item label="版本">{detailSkill.version}</Descriptions.Item>
            <Descriptions.Item label="作者">{detailSkill.author || '-'}</Descriptions.Item>
            <Descriptions.Item label="标签" span={2}>
              {(detailSkill.tags || []).map(t => <Tag key={t}>{t}</Tag>)}
            </Descriptions.Item>
            <Descriptions.Item label="状态" span={2}>
              {detailSkill.enabled ? <Badge status="success" text="启用" /> : <Badge status="default" text="禁用" />}
            </Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{detailSkill.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="SKILL.md" span={2}>
              <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, background: '#f8fafc', padding: 8, borderRadius: 4 }}>
                {detailSkill.skill_md || '(空)'}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="prompt.md" span={2}>
              <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, background: '#f8fafc', padding: 8, borderRadius: 4 }}>
                {detailSkill.prompt_md || '(空)'}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="Schema" span={2}>
              <pre style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, background: '#f8fafc', padding: 8, borderRadius: 4 }}>
                {detailSkill.schema ? JSON.stringify(detailSkill.schema, null, 2) : '(空)'}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">{detailSkill.created_at ? new Date(detailSkill.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{detailSkill.updated_at ? new Date(detailSkill.updated_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
