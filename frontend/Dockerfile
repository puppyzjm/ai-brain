FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
# 国内 npm 镜像 + 超时重试（服务器网络优化；依赖版本不变）
RUN npm install --registry=https://registry.npmmirror.com --fetch-timeout=120000 --fetch-retries=3
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
