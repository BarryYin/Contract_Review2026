# Brief: batch-compare

## Problem
评委要求系统支持批量上传（一次≥5份合同）并在统一Dashboard展示评分概览和风险分布热力图，还需提供两份同类合同的逐条差异对比功能。当前系统只支持单文件处理，完全没有批量能力和对比能力。

## Current State
- 已有：单文件上传、单文件审查、PDF报告导出
- 缺失：批量上传、批量审查、Dashboard概览、热力图、合同对比

## Desired Outcome
- 支持一次上传≥5份合同，批量触发审查
- Dashboard展示所有合同的评分概览和风险等级分布
- 可选择两份同类合同进行逐条款差异对比，高亮显示变化
- 风险分布热力图

## Approach
前端批量上传组件+后端批量处理API+Dashboard页面（表格+图表）+对比页面（双栏对照+差异高亮）。

## Scope
- **In**: 批量上传API、批量审查调度、Dashboard页面、热力图、合同对比页面
- **Out**: 合同分类管理、模板匹配、Webhook通知

## Boundary Candidates
- 批量上传与调度（后端）
- Dashboard可视化（前端）
- 合同对比引擎（后端+前端）

## Out of Boundary
- 不做合同分类/标签系统
- 不做审查结果的持久化数据库（继续用文件存储）
- 不做用户权限管理

## Upstream / Downstream
- **Upstream**: doc-parser(结构化JSON), compliance-engine(审查结果)
- **Downstream**: 无（最终交付层）

## Existing Spec Touchpoints
- **Extends**: 无（全新spec）
- **Adjacent**: report-output（共享前端组件模式）

## Constraints
- 文件存储方案，批量结果仍用JSON文件
- 前端图表库优先用已有的，避免引入新依赖
- Step API有速率限制，批量审查需串行或限并发
