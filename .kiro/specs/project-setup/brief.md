# Brief: project-setup

## Problem
黑客松项目从零开始，需要搭建后端服务、前端应用、开发环境和基础文件处理流程，为后续三个核心spec提供运行基础。

## Current State
绿地项目，仅有一份需求文档和4份测试合同样本。无代码、无配置、无基础设施。

## Desired Outcome
一个可运行的开发环境：FastAPI后端可启动并提供API，React前端可启动并展示基础页面，文件上传/下载流程跑通，项目结构清晰规范。

## Approach
FastAPI后端 + React(Vite + TailwindCSS)前端，前后端分离架构。后端提供REST API，前端通过axios调用。使用uvicorn作为ASGI服务器。

## Scope
- **In**: 后端项目结构(FastAPI)、前端项目结构(React/Vite/Tailwind)、文件上传API、文件下载API、基础目录结构(contracts/, outputs/, uploads/)、CORS配置、API错误处理中间件、开发启动脚本
- **Out**: 业务逻辑（解析、分析、报告）、用户认证、数据库

## Boundary Candidates
- 后端API骨架（路由注册、请求/响应模型）
- 前端页面骨架（路由、布局组件）
- 文件处理基础（上传、存储、下载）

## Out of Boundary
- 文档解析逻辑（doc-parser spec负责）
- 合规分析逻辑（compliance-engine spec负责）
- 报告生成逻辑（report-output spec负责）

## Upstream / Downstream
- **Upstream**: 无
- **Downstream**: doc-parser, compliance-engine, report-output 均依赖此spec提供的基础设施

## Existing Spec Touchpoints
- **Extends**: 无
- **Adjacent**: 无

## Constraints
- Python 3.11+
- Node.js 18+
- 前后端分离，通过REST API通信
- 开发环境需支持热重载
