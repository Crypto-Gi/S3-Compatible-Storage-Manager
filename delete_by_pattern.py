#!/usr/bin/env python3
"""
Script to delete files from S3-compatible bucket by extension or filename pattern.
Configurable via .env file for safe, targeted deletion.

Note: This script requires Python 3.6+ (uses f-strings)
Run with: python3 delete_by_pattern.py
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_r2_client():
    """
    Create and return a boto3 S3 client configured for S3-compatible storage.
    """
    account_id = os.getenv('R2_ACCOUNT_ID')
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    
    if not all([account_id, access_key_id, secret_access_key]):
        raise ValueError("Missing required environment variables. Check your .env file.")
    
    # S3-compatible endpoint format
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name='auto'
    )
    
    return s3_client

def list_all_objects(s3_client, bucket_name, prefix=''):
    """
    List all objects in the bucket with optional prefix.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        prefix: Optional prefix to filter objects
        
    Returns:
        list: List of object keys
    """
    objects = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        if prefix:
            pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        else:
            pages = paginator.paginate(Bucket=bucket_name)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.append(obj['Key'])
    
    except ClientError as e:
        print(f"Error listing objects: {e}")
        return []
    
    return objects

def matches_pattern(filename, extensions, patterns):
    """
    Check if filename matches any extension or pattern.
    
    Args:
        filename: File name to check
        extensions: List of extensions (e.g., ['.DS_Store', '.docx'])
        patterns: List of patterns to match in filename (e.g., ['temp', 'backup'])
        
    Returns:
        tuple: (matches, reason) - True if matches with reason string
    """
    # Check exact filename match (for files like .DS_Store)
    for ext in extensions:
        if filename == ext or filename.endswith('/' + ext):
            return True, f"exact match: {ext}"
    
    # Check file extension
    for ext in extensions:
        if ext.startswith('.') and filename.lower().endswith(ext.lower()):
            return True, f"extension: {ext}"
    
    # Check if filename contains pattern
    for pattern in patterns:
        if pattern.lower() in filename.lower():
            return True, f"contains: {pattern}"
    
    return False, ""

def delete_by_pattern(bucket_name, extensions, patterns, prefix='', dry_run=False):
    """
    Delete files matching extensions or patterns.
    
    Args:
        bucket_name: Name of the bucket
        extensions: List of file extensions to delete
        patterns: List of patterns to match in filenames
        prefix: Optional prefix to limit scope
        dry_run: If True, only show what would be deleted
    """
    s3_client = get_r2_client()
    
    print(f"Scanning bucket: {bucket_name}")
    if prefix:
        print(f"With prefix: {prefix}")
    print()
    
    # Get all objects
    all_objects = list_all_objects(s3_client, bucket_name, prefix)
    
    if not all_objects:
        print("No objects found in bucket.")
        return
    
    print(f"Found {len(all_objects)} total objects")
    print(f"Filtering by:")
    if extensions:
        print(f"  Extensions: {', '.join(extensions)}")
    if patterns:
        print(f"  Patterns: {', '.join(patterns)}")
    print()
    
    # Find matching objects
    matching_objects = []
    for obj_key in all_objects:
        filename = obj_key.split('/')[-1]  # Get just the filename
        matches, reason = matches_pattern(obj_key, extensions, patterns)
        if matches:
            matching_objects.append((obj_key, reason))
    
    if not matching_objects:
        print("No matching files found.")
        return
    
    # Show preview
    print(f"{'='*60}")
    print(f"Found {len(matching_objects)} files to delete:")
    print(f"{'='*60}\n")
    
    # Show first 20 examples
    for i, (obj_key, reason) in enumerate(matching_objects[:20]):
        print(f"  {obj_key} ({reason})")
    
    if len(matching_objects) > 20:
        print(f"\n  ... and {len(matching_objects) - 20} more files")
    
    print(f"\n{'='*60}")
    
    if dry_run:
        print("DRY RUN MODE - No files will be deleted")
        return
    
    # Confirmation
    print(f"⚠️  WARNING: This will permanently delete {len(matching_objects)} files!")
    confirmation = input("Type 'DELETE' to confirm: ")
    
    if confirmation != 'DELETE':
        print("Operation cancelled.")
        return
    
    # Delete objects
    print(f"\n{'='*60}")
    print("Deleting files...")
    print(f"{'='*60}\n")
    
    deleted_count = 0
    error_count = 0
    
    # Delete in batches of 1000 (S3 limit)
    batch_size = 1000
    for i in range(0, len(matching_objects), batch_size):
        batch = matching_objects[i:i + batch_size]
        
        # Prepare delete request
        objects_to_delete = [{'Key': obj_key} for obj_key, _ in batch]
        
        try:
            response = s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={
                    'Objects': objects_to_delete,
                    'Quiet': False
                }
            )
            
            # Count successful deletions
            if 'Deleted' in response:
                deleted_count += len(response['Deleted'])
                for obj in response['Deleted']:
                    print(f"  ✓ Deleted: {obj['Key']}")
            
            # Report errors
            if 'Errors' in response:
                error_count += len(response['Errors'])
                for error in response['Errors']:
                    print(f"  ✗ Error deleting {error['Key']}: {error['Code']} - {error['Message']}")
        
        except ClientError as e:
            print(f"Error in batch deletion: {e}")
            error_count += len(batch)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Deletion complete!")
    print(f"Successfully deleted: {deleted_count} files")
    if error_count > 0:
        print(f"Errors encountered: {error_count} files")
    print(f"{'='*60}")

def main():
    """Main function to execute the deletion script."""
    bucket_name = os.getenv('R2_BUCKET')
    prefix = os.getenv('R2_PREFIX', '')
    
    # Read deletion patterns from .env
    delete_extensions = os.getenv('DELETE_EXTENSIONS', '')
    delete_patterns = os.getenv('DELETE_PATTERNS', '')
    dry_run = os.getenv('DELETE_DRY_RUN', 'false').lower() == 'true'
    
    if not bucket_name:
        print("Error: R2_BUCKET not set in .env file")
        sys.exit(1)
    
    # Parse extensions and patterns
    extensions = [ext.strip() for ext in delete_extensions.split(',') if ext.strip()]
    patterns = [pat.strip() for pat in delete_patterns.split(',') if pat.strip()]
    
    if not extensions and not patterns:
        print("Error: No deletion criteria specified.")
        print("\nAdd to your .env file:")
        print("DELETE_EXTENSIONS=.DS_Store,.docx,.tmp")
        print("DELETE_PATTERNS=backup,temp,old")
        print("\nOr use both for combined filtering.")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"S3-Compatible Storage Pattern Deletion Tool")
    print(f"Bucket: {bucket_name}")
    if dry_run:
        print(f"Mode: DRY RUN (preview only)")
    print(f"{'='*60}\n")
    
    delete_by_pattern(bucket_name, extensions, patterns, prefix, dry_run)

if __name__ == "__main__":
    main()
