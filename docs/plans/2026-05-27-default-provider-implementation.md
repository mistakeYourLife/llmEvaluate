# Default Provider Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为供应商增加唯一默认逻辑，让录制样本代理请求始终走“默认且启用”的供应商。

**Architecture:** 在 `provider` 模型新增 `is_default` 字段，并由仓储层统一维护“唯一默认”的约束。管理后台提供默认供应商展示与切换接口，代理录制入口改为只读取默认供应商；如果没有默认且启用的供应商，则直接报错，不再退回到“第一个启用供应商”。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React, TypeScript, Vitest, Pytest

---

### Task 1: 默认供应商后端测试

**Files:**
- Modify: `tests/admin/test_providers_api.py`
- Modify: `tests/api/test_proxy_recording.py`

**Step 1: Write the failing test**

- 覆盖首个供应商自动成为默认
- 覆盖切换默认供应商
- 覆盖默认供应商不能禁用和删除
- 覆盖代理录制优先走默认供应商

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/admin/test_providers_api.py tests/api/test_proxy_recording.py`

**Step 3: Write minimal implementation**

- 新增模型字段与仓储方法
- 新增后台接口和代理查询逻辑

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/admin/test_providers_api.py tests/api/test_proxy_recording.py`

### Task 2: 数据模型与迁移

**Files:**
- Modify: `data/models/provider.py`
- Modify: `data/repositories/provider_repository.py`
- Create: `alembic/versions/20260527_000003_add_default_provider.py`

**Step 1: Write the failing migration-sensitive test**

- 通过 API/代理测试覆盖 `Base.metadata.create_all` 路径
- 通过 Alembic 迁移覆盖已有库升级路径

**Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/admin/test_providers_api.py tests/api/test_proxy_recording.py`

**Step 3: Write minimal implementation**

- 增加 `is_default`
- 创建时在无默认供应商时自动设为默认
- 设为默认时清空其他供应商的默认标记
- 迁移时把现有“最小 id 的已启用供应商”设为默认

**Step 4: Run test to verify it passes**

Run: `./.venv/bin/pytest tests/admin/test_providers_api.py tests/api/test_proxy_recording.py tests/data/test_migrations_smoke.py`

### Task 3: 管理后台前端交互

**Files:**
- Modify: `admin/web/src/api/client.ts`
- Modify: `admin/web/src/App.tsx`
- Modify: `admin/web/src/App.test.tsx`

**Step 1: Write the failing test**

- 供应商列表显示默认标识
- 点击“设为默认”会调用新接口并刷新显示
- 默认供应商按钮禁用或隐藏重复操作

**Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

**Step 3: Write minimal implementation**

- 扩展 Provider 类型
- 新增“设为默认”接口调用
- 列表增加默认标记与按钮

**Step 4: Run test to verify it passes**

Run: `npm test -- --run src/App.test.tsx`

### Task 4: 全量验证

**Files:**
- Verify only

**Step 1: Run backend verification**

Run: `./.venv/bin/pytest tests/admin/test_providers_api.py tests/api/test_proxy_recording.py`

**Step 2: Run frontend verification**

Run: `cd admin/web && npm test -- --run src/App.test.tsx && npm run build`

**Step 3: Run migration verification**

Run: `./.venv/bin/alembic upgrade head`
