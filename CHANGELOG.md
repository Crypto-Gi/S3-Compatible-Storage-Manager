# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [v0.3] - 2024-11-25

### Added
- **Move directory script**: New `move_r2_directory.py` for relocating directories within bucket
- Copy-then-delete operation for safe directory moves
- Preview mode showing what will be moved before execution
- Progress tracking for move operations
- Helper script `run_move.sh` for easy execution

### Features
- Move entire directories while preserving structure
- Handles any number of objects efficiently
- Detailed error reporting and recovery
- Customizable move operations via configuration

### Use Cases
- Reorganize bucket structure
- Consolidate directories under common parent
- Rename directory paths

## [v0.2] - 2024-11-08

### Added
- **Incremental upload feature**: Upload script now checks existing files in R2 before uploading
- Pre-upload analysis showing files to upload vs skip
- Memory-efficient in-memory comparison (uses ~150 bytes per file path)
- Detailed statistics showing uploaded and skipped file counts and sizes

### Changed
- Upload script now scans R2 bucket before uploading
- Upload script builds local file list with intended R2 paths
- Enhanced progress reporting with skip notifications
- Improved summary statistics with separate counts for uploaded and skipped files

### Technical Details
- Uses `list_objects_v2` with pagination to fetch all existing objects
- Stores existing object keys in a Python set for O(1) lookup performance
- Memory usage: ~30 MB for 100K files, ~750 MB for 5M files
- Comparison happens in-memory before any uploads begin

## [v0.1] - 2024-11-08

### Added
- Initial release
- Upload script to upload directories to R2 with hierarchy preservation
- Delete script to batch delete all objects from R2 bucket
- Helper scripts for easy execution
- Comprehensive README with usage instructions
- .gitignore for Python and environment files
