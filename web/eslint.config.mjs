import next from "eslint-config-next";

const config = [...next, { ignores: [".next/**", "src/lib/api-types.ts", "e2e/.auth/**"] }];

export default config;
