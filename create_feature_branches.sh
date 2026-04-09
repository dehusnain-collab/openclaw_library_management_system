#!/bin/bash
# Script to create feature branches for Jira tickets

echo "Creating feature branches..."

# Make sure we're on main branch
git checkout main

# Sprint 1 - Completed
echo "# Sprint 1: Foundation & Core Authentication"
echo "# ✅ SCRUM-11: Project Structure & Core Setup - COMPLETED"
echo "# ✅ SCRUM-12: Create project folder structure - COMPLETED"
echo "# ✅ SCRUM-13: Database Layer & Migrations - COMPLETED"

# Sprint 1 - Next
echo ""
echo "# 🔄 SCRUM-15: User Registration & Login - NEXT"
git checkout -b feature/SCRUM-15-user-registration-login
git checkout main

echo ""
echo "# ⏳ SCRUM-22: Password Management"
echo "# git checkout -b feature/SCRUM-22-password-management"

echo ""
echo "# ⏳ SCRUM-14: Authentication & Security Module (Epic)"
echo "# git checkout -b feature/SCRUM-14-authentication-security-module"

# Sprint 2
echo ""
echo "# Sprint 2: RBAC & Core Management"
echo "# ⏳ SCRUM-16: Role-Based Access Control"
echo "# git checkout -b feature/SCRUM-16-role-based-access-control"

echo ""
echo "# ⏳ SCRUM-17: Role & Permission System"
echo "# git checkout -b feature/SCRUM-17-role-permission-system"

echo ""
echo "# ⏳ SCRUM-23: Admin Role Management"
echo "# git checkout -b feature/SCRUM-23-admin-role-management"

echo ""
echo "# ⏳ SCRUM-24: User Management"
echo "# git checkout -b feature/SCRUM-24-user-management"

echo ""
echo "# ⏳ SCRUM-25: User Profile Management"
echo "# git checkout -b feature/SCRUM-25-user-profile-management"

echo ""
echo "# ⏳ SCRUM-26: User Deactivation"
echo "# git checkout -b feature/SCRUM-26-user-deactivation"

echo ""
echo "✅ Branch creation script ready!"
echo "First, work on: feature/SCRUM-15-user-registration-login"
