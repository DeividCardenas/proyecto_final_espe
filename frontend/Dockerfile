# ==============================================================================
# ETAPA 1: Construcción y Compilación de Assets (Node.js)
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ==============================================================================
# ETAPA 2: Servidor Web de Producción (Nginx Alpine)
# ==============================================================================
FROM nginx:1.27-alpine AS production

RUN rm -rf /usr/share/nginx/html/* && mkdir -p /var/cache/nginx/tiles

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
