FROM node:22

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_DISABLE_GEOLOCATION=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_DISABLE_GEOLOCATION=$NEXT_PUBLIC_DISABLE_GEOLOCATION

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY . .

RUN pnpm install --force

RUN pnpm next build

EXPOSE 3000

CMD ["pnpm", "next", "start"]
