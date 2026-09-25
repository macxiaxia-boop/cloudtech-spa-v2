#!/bin/bash
# Phase 48.A · SPA 部署脚本（红线 #22 边界版）
# 状态：内部资源·AI 已完成·付费域名/服务器待用户拍板

set -e

# ============ 配置 ============
APP_NAME="cloud-saas"
GIT_REPO="git@github.com:cloud/cloud-saas.git"
DOMAIN="${CLOUD_DOMAIN:-cloud.example.com}"
STAGING_DOMAIN="staging.cloud.example.com"
SSL_EMAIL="${SSL_EMAIL:-admin@cloud.example.com}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
err() { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }

# ============ 前置检查 ============
check_requirements() {
    log "检查依赖..."
    command -v docker >/dev/null 2>&1 || err "Docker 未安装"
    command -v docker-compose >/dev/null 2>&1 || err "Docker Compose 未安装"
    command -v nginx >/dev/null 2>&1 || warn "Nginx 未安装（生产环境强烈建议）"
    command -v certbot >/dev/null 2>&1 || warn "Certbot 未安装（SSL 证书）"
    log "依赖检查完成 ✓"
}

# ============ 构建镜像 ============
build_image() {
    log "构建 Docker 镜像..."
    cd "$(dirname "$0")/.."
    docker build -t ${APP_NAME}:latest .
    log "镜像构建完成 ✓"
}

# ============ 启动服务 ============
start_services() {
    log "启动服务..."
    docker-compose up -d
    sleep 5
    log "服务启动完成 ✓"
    echo ""
    log "健康检查..."
    curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/api/v2/health || warn "本地健康检查失败"
}

# ============ 部署到服务器 ============
deploy_to_server() {
    local env=${1:-production}

    log "部署到 ${env}..."

    # 红线 #22 边界检查
    if [ "$env" = "production" ]; then
        warn "===== 红线 #22 边界 ====="
        warn "生产环境部署涉及："
        warn "  - 服务器付费（已采购？需要用户授权）"
        warn "  - 域名解析（DNS 已配置？需要用户授权）"
        warn "  - SSL 证书（已申请？需要用户授权）"
        warn "确认继续？[y/N]"
        read -r confirm
        if [ "$confirm" != "y" ]; then
            err "用户取消部署"
        fi
    fi

    # 部署到预发布
    if [ "$env" = "staging" ]; then
        log "部署到预发布 (${STAGING_DOMAIN})..."
        rsync -avz --delete \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='.venv' \
            ./ deploy@${STAGING_DOMAIN}:/opt/${APP_NAME}/

        ssh deploy@${STAGING_DOMAIN} << EOF
            cd /opt/${APP_NAME}
            docker-compose pull
            docker-compose up -d
            sleep 5
            curl -s -o /dev/null -w "Staging Health: HTTP %{http_code}\n" https://${STAGING_DOMAIN}/api/v2/health
EOF
        log "预发布部署完成 ✓"
    fi

    # 部署到生产
    if [ "$env" = "production" ]; then
        log "部署到生产 (${DOMAIN})..."
        rsync -avz --delete \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='.venv' \
            ./ deploy@${DOMAIN}:/opt/${APP_NAME}/

        ssh deploy@${DOMAIN} << EOF
            cd /opt/${APP_NAME}
            docker-compose pull
            docker-compose up -d
            sleep 10
            curl -s -o /dev/null -w "Production Health: HTTP %{http_code}\n" https://${DOMAIN}/api/v2/health
EOF
        log "生产部署完成 ✓"
    fi
}

# ============ SSL 证书 ============
setup_ssl() {
    log "申请 SSL 证书..."
    warn "===== 红线 #22 边界 ====="
    warn "SSL 证书申请涉及："
    warn "  - Let's Encrypt 邮箱（需要用户授权）"
    warn "  - 域名所有权验证（DNS 已配置？）"
    warn "确认继续？[y/N]"
    read -r confirm
    if [ "$confirm" != "y" ]; then
        err "用户取消 SSL 申请"
    fi

    sudo certbot --nginx \
        -d ${DOMAIN} \
        -d www.${DOMAIN} \
        --non-interactive \
        --agree-tos \
        --email ${SSL_EMAIL} \
        --redirect

    log "SSL 证书申请完成 ✓"
}

# ============ 备份 ============
backup() {
    log "备份当前版本..."
    ssh deploy@${DOMAIN} << EOF
        if [ -d /opt/${APP_NAME}/.backup ]; then
            rm -rf /opt/${APP_NAME}/.backup
        fi
        mv /opt/${APP_NAME} /opt/${APP_NAME}/.backup
EOF
    log "备份完成 ✓"
}

# ============ 回滚 ============
rollback() {
    log "回滚到上一版本..."
    ssh deploy@${DOMAIN} << EOF
        if [ -d /opt/${APP_NAME}/.backup ]; then
            rm -rf /opt/${APP_NAME}
            mv /opt/${APP_NAME}/.backup /opt/${APP_NAME}
            cd /opt/${APP_NAME}
            docker-compose up -d
            log "回滚完成 ✓"
        else
            err "无备份可回滚"
        fi
EOF
}

# ============ 主菜单 ============
case "$1" in
    check) check_requirements ;;
    build) build_image ;;
    start) start_services ;;
    deploy:staging) deploy_to_server staging ;;
    deploy:prod) deploy_to_server production ;;
    ssl) setup_ssl ;;
    backup) backup ;;
    rollback) rollback ;;
    *)
        echo "用法: $0 {check|build|start|deploy:staging|deploy:prod|ssl|backup|rollback}"
        echo ""
        echo "示例:"
        echo "  $0 check                    # 检查依赖"
        echo "  $0 build                    # 构建镜像"
        echo "  $0 start                    # 本地启动"
        echo "  $0 deploy:staging           # 部署到预发布"
        echo "  $0 deploy:prod              # 部署到生产（红线 #22 必拍板）"
        echo "  $0 ssl                      # 申请 SSL（红线 #22 必拍板）"
        echo "  $0 backup                   # 备份当前版本"
        echo "  $0 rollback                 # 回滚到上一版本"
        exit 1
        ;;
esac
