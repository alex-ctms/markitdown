# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- Docker web app (`webapp/`) with drag-and-drop file conversion UI
- Bulk upload support — drop multiple files simultaneously
- Raw / rendered Markdown preview toggle in web UI
- Copy-to-clipboard and single-file `.md` download
- Download All — exports all converted files as a `.zip` via server-side endpoint
- `docker-compose.yml` for one-command local deployment

---

## [0.1.6] — 2025

### Added
- Azure Content Understanding converter

### Fixed
- Recursive HTML parsing no longer triggers `RecursionError` on deeply nested documents
- PDF conversion memory growth resolved by calling `page.close()` after each page

---

## [0.1.5] — 2025

### Added
- OCR layer service for embedded images and PDF scans
- Aligned Markdown output for PDF table extraction
- Wide table support

### Fixed
- PDF parsing failure on partially numbered lists
- `fix docx parse error` — newline in alt text no longer breaks DOCX parse
- Correctly pass custom LLM prompt parameter

### Changed
- Updated `mammoth` to 1.11.0
- Updated `pdfminer.six` dependency

---

## [0.1.4] — 2025

### Added
- Checkbox support in Markdown converter
- `data-src` attribute support for HTML images
- HTML support in DocumentIntelligenceConverter
- `text/markdown` added to Accept header for URL fetches

### Fixed
- PPTX shapes with `None` position no longer crash conversion
- ExifTool usage hardened — require version ≥ 12.24

### Changed
- Removed `onnxruntime<=1.20.1` Windows pin

---

## [0.1.0] — 2024

### Added
- Initial release
- PDF, PowerPoint, Word, Excel conversion
- Image conversion (EXIF metadata + OCR)
- Audio conversion (EXIF metadata + speech transcription)
- HTML, CSV, JSON, XML support
- ZIP file iteration
- YouTube URL transcription
- EPub support
- Plugin system
- CLI (`markitdown`) and Python API
- Azure Document Intelligence integration
