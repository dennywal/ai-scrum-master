#!/usr/bin/env python3
"""
Example: Process a TDD document and create GitHub issues.

This example demonstrates how to:
1. Parse a TDD document
2. Extract tasks from the content
3. Analyze priorities and dependencies
4. Create GitHub issues from the tasks
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.documents import DocumentInput
from src.agents.document_parser import DocumentParser
from src.agents.task_extractor import TaskExtractor
from src.agents.priority_analyzer import PriorityAnalyzer
from src.agents.dependency_resolver import DependencyResolver
from src.agents.issue_mapper import IssueMapper
from src.integrations.github_client import GitHubIssueCreator
from src.config.settings import settings


def main():
    """Main example function."""
    
    # Sample TDD document content
    tdd_content = """
    # User Authentication System TDD
    
    ## Overview
    This document outlines the test-driven development approach for implementing 
    a secure user authentication system with JWT tokens.
    
    ## Test Cases
    
    ### User Registration Tests
    - Test successful user registration with valid email and password
    - Test registration fails with duplicate email
    - Test registration fails with weak password
    - Test email verification token is sent after registration
    - Test user cannot login without email verification
    
    ### User Login Tests  
    - Test successful login with correct credentials
    - Test login fails with incorrect password
    - Test login fails with non-existent email
    - Test account locks after 5 failed login attempts
    - Test JWT token is returned on successful login
    - Test refresh token mechanism works correctly
    
    ### Password Reset Tests
    - Test password reset email is sent for valid user
    - Test password reset token expires after 1 hour
    - Test user can set new password with valid token
    - Test old password no longer works after reset
    
    ## Implementation Requirements
    
    ### Security Requirements
    - Use bcrypt for password hashing with salt rounds of 10
    - Implement JWT tokens with RS256 algorithm
    - Add rate limiting to prevent brute force attacks
    - Store refresh tokens securely in database
    - Implement CSRF protection for state-changing operations
    
    ### Database Requirements
    - User table with email, password_hash, created_at, updated_at
    - Session table for refresh token management
    - Password reset token table with expiration
    - Failed login attempts tracking table
    
    ### API Endpoints
    - POST /api/auth/register - User registration
    - POST /api/auth/login - User login
    - POST /api/auth/logout - User logout
    - POST /api/auth/refresh - Token refresh
    - POST /api/auth/reset-password - Request password reset
    - POST /api/auth/reset-password/confirm - Confirm password reset
    
    ## Acceptance Criteria
    - All authentication endpoints must respond within 200ms
    - Password hashing must use bcrypt with minimum 10 salt rounds
    - JWT tokens must expire after 15 minutes
    - Refresh tokens must expire after 7 days
    - System must handle 1000 concurrent authentication requests
    - All sensitive operations must be logged for audit purposes
    
    ## Dependencies
    - Database setup must be completed first
    - Email service integration required for notifications
    - Redis required for rate limiting implementation
    """
    
    print("AI Scrum Master - TDD Processing Example")
    print("=" * 50)
    
    # Step 1: Parse the document
    print("\n1. Parsing TDD document...")
    parser = DocumentParser()
    try:
        tdd_sections = parser.parse_tdd_document(tdd_content)
        print(f"   ✓ Found {len(tdd_sections.test_cases)} test cases")
        print(f"   ✓ Found {len(tdd_sections.implementation_requirements)} implementation requirements")
    except Exception as e:
        print(f"   ✗ Parsing failed: {e}")
        return
    
    # Step 2: Extract tasks
    print("\n2. Extracting tasks from sections...")
    extractor = TaskExtractor()
    try:
        tasks = extractor.extract_tasks_from_tdd(tdd_sections)
        print(f"   ✓ Extracted {len(tasks)} tasks")
        for task in tasks[:3]:  # Show first 3 tasks
            print(f"      - {task.title}")
    except Exception as e:
        print(f"   ✗ Task extraction failed: {e}")
        return
    
    # Step 3: Analyze priorities
    print("\n3. Analyzing task priorities...")
    analyzer = PriorityAnalyzer()
    try:
        prioritized_tasks = analyzer.analyze_priorities_batch(tasks)
        high_priority = [t for t in prioritized_tasks if t.priority == "high"]
        print(f"   ✓ Identified {len(high_priority)} high-priority tasks")
    except Exception as e:
        print(f"   ✗ Priority analysis failed: {e}")
        return
    
    # Step 4: Resolve dependencies
    print("\n4. Resolving task dependencies...")
    resolver = DependencyResolver()
    try:
        ordered_tasks = resolver.resolve_dependencies(prioritized_tasks)
        print(f"   ✓ Tasks ordered successfully")
        print(f"   ✓ No circular dependencies detected")
    except Exception as e:
        print(f"   ✗ Dependency resolution failed: {e}")
        return
    
    # Step 5: Map to GitHub issues
    print("\n5. Mapping tasks to GitHub issue format...")
    mapper = IssueMapper()
    try:
        issue_templates = []
        for task in ordered_tasks:
            template = mapper.map_task_to_issue(task)
            issue_templates.append(template)
        print(f"   ✓ Created {len(issue_templates)} issue templates")
    except Exception as e:
        print(f"   ✗ Issue mapping failed: {e}")
        return
    
    # Step 6: Create issues (dry run by default)
    print("\n6. Creating GitHub issues (dry run)...")
    print("   Note: Set GITHUB_TOKEN and specify repo to actually create issues")
    
    # Uncomment to actually create issues:
    # creator = GitHubIssueCreator(settings.github.github_token.get_secret_value())
    # result = creator.create_issues_batch(
    #     repo_owner="your-org",
    #     repo_name="your-repo",
    #     templates=issue_templates
    # )
    # print(f"   ✓ Created {len(result.created_issues)} issues")
    # print(f"   ✓ Success rate: {result.success_rate * 100:.1f}%")
    
    # Show example issue output
    print("\n" + "=" * 50)
    print("Example Generated Issue:")
    print("=" * 50)
    if issue_templates:
        example = issue_templates[0]
        print(f"\nTitle: {example.title}")
        print(f"Labels: {', '.join(example.labels)}")
        print(f"\nBody:\n{example.body[:500]}...")  # Show first 500 chars
    
    print("\n" + "=" * 50)
    print("Processing complete!")
    print(f"Total tasks extracted: {len(tasks)}")
    print(f"Ready to create: {len(issue_templates)} GitHub issues")


if __name__ == "__main__":
    main()