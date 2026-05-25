FROM node:22

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY . .

RUN pnpm install --force

RUN pnpm next build

EXPOSE 3000

CMD ["pnpm", "next", "start"]
