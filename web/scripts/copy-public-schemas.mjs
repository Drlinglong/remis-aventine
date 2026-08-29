import { copyFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('../../src/remis_aventine/schemas/v03-zh-en-public-result.schema.json', import.meta.url));
const destinationDirectory = fileURLToPath(new URL('../dist/schemas/', import.meta.url));
const destination = fileURLToPath(new URL('../dist/schemas/v03-zh-en-public-result.schema.json', import.meta.url));

await mkdir(destinationDirectory, { recursive: true });
await copyFile(source, destination);
