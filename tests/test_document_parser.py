"""Tests for DocumentParser class."""

import pytest

from src.agents.document_parser import DocumentParser
from src.core.exceptions import DocumentParsingError
from src.models.documents import DocumentType


class TestDocumentParser:
    """Test suite for DocumentParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()

    def test_parse_tdd_with_all_sections(self):
        """Test parsing a complete TDD document."""
        tdd_content = """
# TDD: User Authentication System

## Overview
This document describes the test-driven development approach for the user authentication system.

## Test Cases
- User can register with email and password
- User can login with valid credentials
- Invalid credentials are rejected
- Password reset functionality works

## Implementation Requirements
- Use JWT for authentication
- Store passwords using bcrypt
- Implement rate limiting
- Add session management

## Acceptance Criteria
- All authentication endpoints return proper status codes
- JWT tokens expire after 24 hours
- Failed login attempts are logged
- Users receive email confirmation

## Dependencies
- Database connection module
- Email service
- JWT library
- Bcrypt library
        """

        result = self.parser.parse_tdd_document(tdd_content)

        assert result.overview is not None
        assert "test-driven development approach" in result.overview
        assert len(result.test_cases) == 4
        assert "User can register" in result.test_cases[0]
        assert len(result.implementation_requirements) == 4
        assert "JWT for authentication" in result.implementation_requirements[0]
        assert len(result.acceptance_criteria) == 4
        assert len(result.dependencies) == 4
        assert result.is_valid()

    def test_parse_tdd_minimal_valid(self):
        """Test parsing minimal valid TDD document."""
        tdd_content = """
## Test Cases
- Test user login
- Test user logout
        """

        result = self.parser.parse_tdd_document(tdd_content)

        assert result.overview is None
        assert len(result.test_cases) == 2
        assert result.is_valid()

    def test_parse_tdd_empty_document_raises_error(self):
        """Test empty TDD document raises error."""
        with pytest.raises(DocumentParsingError) as exc_info:
            self.parser.parse_tdd_document("")
        
        assert "Document is empty" in str(exc_info.value)

    def test_parse_tdd_no_valid_sections_raises_error(self):
        """Test TDD without valid sections raises error."""
        tdd_content = """
# Random Document
Some content without any TDD sections.
        """

        with pytest.raises(DocumentParsingError) as exc_info:
            self.parser.parse_tdd_document(tdd_content)
        
        assert "No valid test cases or requirements found" in str(exc_info.value)

    def test_parse_prd_with_all_sections(self):
        """Test parsing a complete PRD document."""
        prd_content = """
# PRD: E-Commerce Platform

## Executive Summary
Building a modern e-commerce platform for small businesses.

## Features

### User Management
- User registration and login
- Profile management
- Order history

### Product Catalog
- Product listing
- Search and filtering
- Category navigation

## Technical Requirements
- Microservices architecture
- PostgreSQL database
- Redis caching
- Docker deployment

## User Stories
- As a customer, I want to browse products
- As a customer, I want to add items to cart
- As a seller, I want to manage inventory
- As an admin, I want to view analytics

## Dependencies
- Payment Gateway: Stripe API
- Email Service: SendGrid
- CDN: CloudFront

## Success Metrics
- Page load time < 2 seconds
- 99.9% uptime
- < 1% cart abandonment rate
        """

        result = self.parser.parse_prd_document(prd_content)

        assert result.executive_summary is not None
        assert "modern e-commerce platform" in result.executive_summary
        assert len(result.features) == 2
        assert result.features[0]["name"] == "User Management"
        assert len(result.features[0]["requirements"]) == 3
        assert len(result.technical_requirements) == 4
        assert len(result.user_stories) == 4
        assert "Payment Gateway" in result.dependencies
        assert len(result.success_metrics) == 3
        assert result.is_valid()

    def test_parse_prd_minimal_valid(self):
        """Test parsing minimal valid PRD document."""
        prd_content = """
## Features
- User authentication
- Data storage
        """

        result = self.parser.parse_prd_document(prd_content)

        assert result.executive_summary is None
        assert len(result.features) == 2
        assert result.is_valid()

    def test_parse_prd_empty_document_raises_error(self):
        """Test empty PRD document raises error."""
        with pytest.raises(DocumentParsingError) as exc_info:
            self.parser.parse_prd_document("")
        
        assert "Document is empty" in str(exc_info.value)

    def test_parse_prd_no_valid_sections_raises_error(self):
        """Test PRD without valid sections raises error."""
        prd_content = """
# Random Document
Some content without any PRD sections.
        """

        with pytest.raises(DocumentParsingError) as exc_info:
            self.parser.parse_prd_document(prd_content)
        
        assert "No valid features or user stories found" in str(exc_info.value)

    def test_extract_list_items_various_formats(self):
        """Test extracting list items from various formats."""
        content = """
- Item with dash
* Item with asterisk
+ Item with plus
• Item with bullet
1. Numbered item
2) Another numbered item
Plain text line
        """

        items = self.parser._extract_list_items(content)

        assert len(items) == 7
        assert "Item with dash" in items
        assert "Item with asterisk" in items
        assert "Item with plus" in items
        assert "Item with bullet" in items
        assert "Numbered item" in items
        assert "Another numbered item" in items
        assert "Plain text line" in items

    def test_parse_markdown_with_nested_sections(self):
        """Test parsing markdown with nested sections."""
        content = """
# Main Title

## Section 1
Content for section 1

### Subsection 1.1
Content for subsection 1.1

### Subsection 1.2
Content for subsection 1.2

## Section 2
Content for section 2
        """

        doc = self.parser._parse_markdown(content, DocumentType.TDD)

        assert doc.title == "Main Title"
        assert len(doc.sections) == 2
        assert doc.sections[0].title == "Section 1"
        assert len(doc.sections[0].subsections) == 2
        assert doc.sections[0].subsections[0].title == "Subsection 1.1"
        assert doc.sections[1].title == "Section 2"

    def test_find_section_case_insensitive(self):
        """Test finding sections is case insensitive."""
        content = """
## TEST CASES
- Test 1

## Implementation Requirements
- Requirement 1
        """

        doc = self.parser._parse_markdown(content, DocumentType.TDD)
        
        # Should find "TEST CASES" when searching for "test"
        test_section = self.parser._find_section(doc, ["test"])
        assert test_section is not None
        assert test_section.title == "TEST CASES"

        # Should find "Implementation Requirements" when searching for "IMPLEMENTATION"
        impl_section = self.parser._find_section(doc, ["IMPLEMENTATION"])
        assert impl_section is not None
        assert impl_section.title == "Implementation Requirements"

    def test_extract_dependencies_various_formats(self):
        """Test extracting dependencies in various formats."""
        content = """
User Service depends on Database Module
Auth Service requires JWT Library, Bcrypt
- Payment: Stripe API, PayPal SDK
- Email Service: SendGrid
        """

        deps = self.parser._extract_dependencies(content)

        assert "User Service" in deps
        assert "Database Module" in deps["User Service"]
        assert "Auth Service" in deps
        assert "JWT Library" in deps["Auth Service"]
        assert "Bcrypt" in deps["Auth Service"]
        assert "Payment" in deps
        assert "Stripe API" in deps["Payment"]

    def test_extract_features_with_subsections(self):
        """Test extracting features from subsections."""
        content = """
## Features

### Feature 1
- Requirement A
- Requirement B

### Feature 2
- Requirement C
        """

        doc = self.parser._parse_markdown(content, DocumentType.PRD)
        features_section = self.parser._find_section(doc, ["features"])
        features = self.parser._extract_features(features_section)

        assert len(features) == 2
        assert features[0]["name"] == "Feature 1"
        assert len(features[0]["requirements"]) == 2
        assert "Requirement A" in features[0]["requirements"]
        assert features[1]["name"] == "Feature 2"
        assert len(features[1]["requirements"]) == 1

    def test_parse_tdd_alternative_section_names(self):
        """Test TDD parsing with alternative section names."""
        tdd_content = """
## Testing
- Test case 1
- Test case 2

## Technical Requirements
- Requirement 1

## Criteria
- Criterion 1

## Prerequisites
- Dependency 1
        """

        result = self.parser.parse_tdd_document(tdd_content)

        assert len(result.test_cases) == 2
        assert len(result.implementation_requirements) == 1
        assert len(result.acceptance_criteria) == 1
        assert len(result.dependencies) == 1
        assert result.is_valid()

    def test_parse_prd_alternative_section_names(self):
        """Test PRD parsing with alternative section names."""
        prd_content = """
## Summary
Executive overview of the product.

## Functionality
- Feature 1
- Feature 2

## Use Cases
- User story 1

## KPIs
- Metric 1
        """

        result = self.parser.parse_prd_document(prd_content)

        assert result.executive_summary is not None
        assert len(result.features) == 2
        assert len(result.user_stories) == 1
        assert len(result.success_metrics) == 1
        assert result.is_valid()