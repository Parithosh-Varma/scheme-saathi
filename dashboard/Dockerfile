FROM node:20-alpine
WORKDIR /app
COPY dashboard/package.json ./
RUN npm install
COPY dashboard/ ./
RUN npm run build
EXPOSE 3000
ENV NEXT_PUBLIC_API_URL=http://backend:8000
CMD ["npm", "start"]
