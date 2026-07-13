import { z } from "zod";
import { DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, ResponseFormat } from "../constants.js";

export const responseFormatField = z
  .nativeEnum(ResponseFormat)
  .default(ResponseFormat.MARKDOWN)
  .describe(
    "Output format: 'markdown' for a human-readable summary or 'json' for the full structured payload"
  );

export const paginationFields = {
  page: z.number().int().min(1).default(1).describe("Page number, 1-indexed"),
  pageSize: z
    .number()
    .int()
    .min(1)
    .max(MAX_PAGE_SIZE)
    .default(DEFAULT_PAGE_SIZE)
    .describe(`Results per page, 1-${MAX_PAGE_SIZE} (default ${DEFAULT_PAGE_SIZE})`),
};

export const claimIdField = z
  .string()
  .min(1)
  .describe("Claim ID, e.g. 'CLM-8841'");
