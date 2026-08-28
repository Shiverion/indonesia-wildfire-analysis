import { readdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const chunkRoot = join(process.cwd(), ".next", "static", "chunks");

function javascriptFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return javascriptFiles(path);
    return entry.isFile() && entry.name.endsWith(".js") ? [path] : [];
  });
}

const files = javascriptFiles(chunkRoot);
const failures = [];

for (const file of files) {
  const result = spawnSync(process.execPath, ["--check", file], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.status !== 0) {
    failures.push(`${file}\n${result.stderr || result.stdout}`);
  }
}

if (failures.length) {
  console.error(`Invalid generated JavaScript in ${failures.length} chunk(s):\n${failures.join("\n")}`);
  process.exit(1);
}

console.log(`Validated JavaScript syntax in ${files.length} generated chunk(s).`);
