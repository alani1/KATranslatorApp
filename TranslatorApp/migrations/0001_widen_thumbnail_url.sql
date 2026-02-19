-- Migration 0001: Widen thumbnail_url column
-- Reason: TSV export from Translation Portal contains thumbnail URLs
--         exceeding the previous 140 character limit, causing DataError
--         on insert in TranslationPortalUpdate.py
-- Applied to production: 2026-02-19

ALTER TABLE `ka-content` MODIFY COLUMN `thumbnail_url` VARCHAR(500);
