import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const openapiSource = resolve(root, "contracts/openapi/openapi.yaml");
const bundledSpec = resolve(root, "contracts/openapi/dist/openapi.yaml");
const generatedRoot = resolve(root, "packages/generated-api");
const kotlinOutput = resolve(generatedRoot, "kotlin");
const typescriptOutput = resolve(generatedRoot, "typescript");
const redoclyCli = resolve(root, "node_modules/@redocly/cli/bin/cli.js");
const generatorCli = resolve(
  root,
  "node_modules/@openapitools/openapi-generator-cli/main.js",
);
const temporaryRoot = mkdtempSync(join(tmpdir(), "love-reply-codegen-"));
const jsonBundle = resolve(temporaryRoot, "openapi.json");
const androidSpec = resolve(temporaryRoot, "android-openapi.json");

function run(args) {
  const result = spawnSync(process.execPath, args, {
    cwd: root,
    stdio: "inherit",
  });
  if (result.status !== 0) {
    throw new Error(`command failed with status ${result.status ?? 1}`);
  }
}

function normalizeGeneratedText(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      normalizeGeneratedText(path);
    } else if (/\.(kt|ts|md)$/.test(entry.name)) {
      const normalized = readFileSync(path, "utf8")
        .replace(/[ \t]+$/gm, "")
        .replace(/\s*$/, "\n");
      writeFileSync(path, normalized);
    }
  }
}

try {
  run([redoclyCli, "bundle", openapiSource, "-o", bundledSpec]);
  run([
    redoclyCli,
    "bundle",
    openapiSource,
    "--ext",
    "json",
    "-o",
    jsonBundle,
  ]);
  const androidDocument = JSON.parse(readFileSync(jsonBundle, "utf8"));
  androidDocument.paths = Object.fromEntries(
    Object.entries(androidDocument.paths).filter(([path]) =>
      !path.startsWith("/admin/"),
    ),
  );
  androidDocument.tags = androidDocument.tags.filter(
    (tag) => tag.name !== "ADMIN_RBAC",
  );
  delete androidDocument.components.securitySchemes.adminBearerAuth;
  writeFileSync(androidSpec, JSON.stringify(androidDocument));

  rmSync(kotlinOutput, { recursive: true, force: true });
  rmSync(typescriptOutput, { recursive: true, force: true });

  run([
    generatorCli,
    "generate",
    "-g",
    "kotlin",
    "-i",
    androidSpec,
    "-o",
    "packages/generated-api/kotlin",
    "--additional-properties",
    [
      "packageName=com.love_reply.generated",
      "apiPackage=com.love_reply.generated.api",
      "modelPackage=com.love_reply.generated.model",
      "library=jvm-retrofit2",
      "serializationLibrary=moshi",
      "useCoroutines=true",
      "dateLibrary=java8",
      "enumPropertyNaming=original",
    ].join(","),
    "--type-mappings",
    "null=kotlin.Any",
    "--global-property",
    "modelDocs=false,apiDocs=false,modelTests=false,apiTests=false",
  ]);

  const wrapperProperties = resolve(
    kotlinOutput,
    "gradle/wrapper/gradle-wrapper.properties",
  );
  writeFileSync(
    wrapperProperties,
    readFileSync(wrapperProperties, "utf8")
      .replace("https\\://services.gradle.org", "https\\://downloads.gradle.org")
      .replace("-all.zip", "-bin.zip"),
  );

  run([
    generatorCli,
    "generate",
    "-g",
    "typescript-fetch",
    "-i",
    "contracts/openapi/dist/openapi.yaml",
    "-o",
    "packages/generated-api/typescript",
    "--additional-properties",
    [
      "npmName=@love-reply/generated-api",
      "supportsES6=true",
      "typescriptThreePlus=true",
      "withInterfaces=true",
      "useSingleRequestParameter=true",
    ].join(","),
    "--type-mappings",
    "null=any",
    "--global-property",
    "modelDocs=false,apiDocs=false,modelTests=false,apiTests=false",
  ]);
  normalizeGeneratedText(kotlinOutput);
  normalizeGeneratedText(typescriptOutput);
} finally {
  rmSync(temporaryRoot, { recursive: true, force: true });
}
