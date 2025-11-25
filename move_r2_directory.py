#!/usr/bin/env python3
"""
Script to move directories within an S3-compatible bucket.
Copies objects to new location and deletes originals.

Note: This script requires Python 3.6+ (uses f-strings)
Run with: python3 move_r2_directory.py
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
    Create and return a boto3 S3 client configured for Cloudflare R2.
    """
    account_id = os.getenv('R2_ACCOUNT_ID')
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    
    if not all([account_id, access_key_id, secret_access_key]):
        raise ValueError("Missing required environment variables. Check your .env file.")
    
    # Cloudflare R2 endpoint format
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name='auto'  # R2 uses 'auto' for region
    )
    
    return s3_client

def list_objects_with_prefix(s3_client, bucket_name, prefix):
    """
    List all objects with a given prefix in the bucket.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        prefix: Prefix to filter objects
        
    Returns:
        list: List of object keys
    """
    objects = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.append(obj['Key'])
    
    except ClientError as e:
        print(f"Error listing objects: {e}")
        return []
    
    return objects

def move_object(s3_client, bucket_name, source_key, destination_key):
    """
    Move an object by copying it to a new location and deleting the original.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        source_key: Source object key
        destination_key: Destination object key
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Copy object to new location
        copy_source = {'Bucket': bucket_name, 'Key': source_key}
        s3_client.copy_object(
            Bucket=bucket_name,
            Key=destination_key,
            CopySource=copy_source
        )
        
        # Delete original object
        s3_client.delete_object(Bucket=bucket_name, Key=source_key)
        
        return True
    
    except ClientError as e:
        print(f"Error moving object {source_key}: {e}")
        return False

def move_directory(bucket_name, source_prefix, destination_prefix):
    """
    Move all objects from source prefix to destination prefix.
    
    Args:
        bucket_name: Name of the bucket
        source_prefix: Source directory prefix (e.g., 'source/ecos-release-notes/')
        destination_prefix: Destination directory prefix (e.g., 'source/HPE Aruba/ecos-release-notes/')
    """
    s3_client = get_r2_client()
    
    # Ensure prefixes end with /
    if not source_prefix.endswith('/'):
        source_prefix += '/'
    if not destination_prefix.endswith('/'):
        destination_prefix += '/'
    
    print(f"Scanning objects in: {source_prefix}")
    objects = list_objects_with_prefix(s3_client, bucket_name, source_prefix)
    
    if not objects:
        print(f"No objects found with prefix: {source_prefix}")
        return
    
    print(f"Found {len(objects)} objects to move\n")
    
    # Show preview
    print(f"{'='*60}")
    print(f"Move Preview:")
    print(f"  From: {source_prefix}")
    print(f"  To: {destination_prefix}")
    print(f"  Objects: {len(objects)}")
    print(f"{'='*60}\n")
    
    # Show first few examples
    print("Example moves:")
    for i, obj_key in enumerate(objects[:5]):
        relative_path = obj_key[len(source_prefix):]
        new_key = destination_prefix + relative_path
        print(f"  {obj_key}")
        print(f"  → {new_key}\n")
    
    if len(objects) > 5:
        print(f"  ... and {len(objects) - 5} more objects\n")
    
    # Confirmation
    confirmation = input("Proceed with move? (yes/no): ")
    if confirmation.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    # Move objects
    print(f"\n{'='*60}")
    print("Starting move operation...")
    print(f"{'='*60}\n")
    
    moved_count = 0
    error_count = 0
    
    for obj_key in objects:
        # Calculate new key
        relative_path = obj_key[len(source_prefix):]
        new_key = destination_prefix + relative_path
        
        print(f"Moving: {obj_key}")
        print(f"  → {new_key}")
        
        if move_object(s3_client, bucket_name, obj_key, new_key):
            moved_count += 1
            print(f"  ✓ Moved successfully\n")
        else:
            error_count += 1
            print(f"  ✗ Failed to move\n")
    
    # Summary
    print(f"{'='*60}")
    print(f"Move complete!")
    print(f"Successfully moved: {moved_count} objects")
    if error_count > 0:
        print(f"Errors encountered: {error_count} objects")
    print(f"{'='*60}")

def main():
    """Main function to execute the move script."""
    bucket_name = os.getenv('R2_BUCKET')
    
    if not bucket_name:
        print("Error: R2_BUCKET not set in .env file")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"S3-Compatible Storage Directory Move Tool")
    print(f"Bucket: {bucket_name}")
    print(f"{'='*60}\n")
    
    # Define move operations
    moves = [
        {
            'source': 'source/ecos-release-notes/',
            'destination': 'source/HPE Aruba/ecos-release-notes/'
        },
        {
            'source': 'source/orch-release-notes/',
            'destination': 'source/HPE Aruba/orch-release-notes/'
        }
    ]
    
    print("Planned moves:")
    for i, move in enumerate(moves, 1):
        print(f"{i}. {move['source']} → {move['destination']}")
    print()
    
    # Process each move
    for move in moves:
        print(f"\n{'='*60}")
        print(f"Processing: {move['source']}")
        print(f"{'='*60}\n")
        
        move_directory(
            bucket_name,
            move['source'],
            move['destination']
        )
        
        print()

if __name__ == "__main__":
    main()
