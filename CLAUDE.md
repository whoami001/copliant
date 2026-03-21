# Compliance Hub - Developer Guide

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_permissions.py -v

# Run specific test class
pytest tests/test_permissions.py::TestRequireRoleDecorator -v

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

## Permission System (RBAC)

### User Roles

| Role | Value | Description |
|------|-------|-------------|
| ENGINEER | "engineer" | R&D engineers filling out compliance forms |
| SECURITY | "security" | Security team reviewing security questionnaires |
| LEGAL | "legal" | Legal team approving declarations |
| ADMIN | "admin" | Superuser with access to all operations |

### Permission Matrix

| Operation | ENGINEER | SECURITY | LEGAL | ADMIN |
|-----------|----------|----------|-------|-------|
| create_declaration | ✓ | ✗ | ✗ | ✓ |
| security_review | ✗ | ✓ | ✗ | ✓ |
| legal_approve | ✗ | ✗ | ✓ | ✓ |
| bulk_import | ✓ | ✗ | ✗ | ✓ |
| export_data | ✗ | ✓ | ✓ | ✓ |
| view_all_records | ✗ | ✓ | ✓ | ✓ |

### Backend Usage

#### @require_role Decorator

Use for endpoint-level role restrictions:

```python
from app.core.permissions import require_role, UserRole

@router.post("/security-review")
@require_role(UserRole.SECURITY, UserRole.ADMIN)
async def security_review_endpoint(...):
    # Only SECURITY and ADMIN can access
    pass

@router.post("/legal-approve")
@require_role(UserRole.LEGAL, UserRole.ADMIN)
async def legal_approve_endpoint(...):
    # Only LEGAL and ADMIN can access
    pass
```

**Key behaviors:**
- ADMIN automatically passes all role checks (superuser exception)
- Empty role list `@require_role()` allows all authenticated users
- Returns 403 with detailed error message listing required roles

#### can() Function

Use for fine-grained permission checks within endpoints:

```python
from app.core.permissions import can

@router.post("", response_model=LegalDeclarationResponse)
async def create_declaration(
    declaration_data: LegalDeclarationCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if not can(current_user, "create_declaration"):
        raise HTTPException(status_code=403, detail="权限不足：只有研发和管理员可以创建法务声明")
    # ... rest of endpoint
```

**Available permissions:**
- `create_declaration` - Create legal declarations (Engineer, Admin)
- `security_review` - Review security questionnaires (Security, Admin)
- `legal_approve` - Approve declarations (Legal, Admin)
- `bulk_import` - Bulk import components (Engineer, Admin)
- `export_data` - Export compliance data (Security, Legal, Admin)

#### Data Filtering (Engineer Role)

Engineers can only see their own records plus legacy NULL data:

```python
from sqlalchemy import or_

@router.get("", response_model=List[ComplianceRecordResponse])
async def list_records(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    query = db.query(ComplianceRecord)

    # Engineer data filtering
    if current_user.role == UserRole.ENGINEER:
        query = query.filter(
            or_(
                ComplianceRecord.filled_by == current_user.id,
                ComplianceRecord.filled_by.is_(None)  # Legacy data
            )
        )

    # Security/Legal/Admin see all records
    return query.offset(skip).limit(limit).all()
```

### Frontend Usage

#### Authentication Pattern

```javascript
let currentUser = null;
let authToken = localStorage.getItem('auth_token');
let authLoading = true;

// authFetch handles 403 automatically
async function authFetch(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${authToken}`
        }
    });

    if (res.status === 403) {
        // Extract required roles from error message
        // Show permission denied modal
        throw new Error('权限不足');
    }

    return res;
}
```

#### Role-Based UI

```javascript
function updateRoleBasedUI(user) {
    // Hide loading, show content
    authLoading = false;

    // Role-based button visibility
    document.querySelectorAll('.engineer-only').forEach(el => {
        el.style.display = (user.role === 'engineer' || user.role === 'admin') ? '' : 'none';
    });

    document.querySelectorAll('.security-only').forEach(el => {
        el.style.display = (user.role === 'security' || user.role === 'admin') ? '' : 'none';
    });

    document.querySelectorAll('.legal-only').forEach(el => {
        el.style.display = (user.role === 'legal' || user.role === 'admin') ? '' : 'none';
    });
}
```

#### 403 Permission Denied Modal

```javascript
function showPermissionDenied(requiredRoles) {
    const modal = document.getElementById('permission-denied-modal-overlay');
    const rolesList = document.getElementById('required-roles-list');

    rolesList.innerHTML = requiredRoles.map(role =>
        `<li>${role}</li>`
    ).join('');

    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
}

function closePermissionDeniedModal() {
    const modal = document.getElementById('permission-denied-modal-overlay');
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
}
```

**Accessibility:**
- Modal uses `role="dialog"` and `aria-modal="true"`
- Focus trap prevents tabbing outside modal
- ESC key closes modal
- Proper aria-labelledby and aria-describedby

### Testing

#### Test Fixtures

```python
@pytest.fixture
def engineer(db_session):
    return User(id=1, email="engineer@test.com", role=UserRole.ENGINEER, is_active=True)

@pytest.fixture
def security(db_session):
    return User(id=2, email="security@test.com", role=UserRole.SECURITY, is_active=True)

@pytest.fixture
def legal(db_session):
    return User(id=3, email="legal@test.com", role=UserRole.LEGAL, is_active=True)

@pytest.fixture
def admin(db_session):
    return User(id=4, email="admin@test.com", role=UserRole.ADMIN, is_active=True)
```

#### Permission Tests

```python
# Test role-based access
def test_require_role_allows_correct_role(self, db_session):
    user = User(role=UserRole.ENGINEER, is_active=True)
    assert has_permission(user, [UserRole.ENGINEER]) is True
    assert has_permission(user, [UserRole.SECURITY]) is False

# Test ADMIN pass-through
def test_require_role_admin_access(self, db_session):
    admin = User(role=UserRole.ADMIN, is_active=True)
    assert has_permission(admin, [UserRole.ENGINEER]) is True
    assert has_permission(admin, []) is True  # Empty list passes

# Test can() function
def test_can_create_declaration(self, db_session):
    assert can(engineer, "create_declaration") is True
    assert can(admin, "create_declaration") is True
    assert can(security, "create_declaration") is False
```

## Project Structure

```
compliance-hub/
├── app/
│   ├── core/
│   │   └── permissions.py      # RBAC: require_role, can(), has_permission
│   ├── models/
│   │   ├── user.py             # User, UserRole enum
│   │   ├── compliance_record.py
│   │   └── legal_declaration.py
│   ├── routes/
│   │   ├── records.py          # Compliance record endpoints (+data filtering)
│   │   ├── legal_declarations.py
│   │   └── components.py
│   └── schemas/
├── tests/
│   ├── conftest.py             # pytest fixtures (engineer, security, legal, admin)
│   └── test_permissions.py     # Permission system tests
├── static/
│   └── index.html              # Frontend with role-based UI
├── pytest.ini
└── pyproject.toml
```

## Key Conventions

1. **Always check permissions** - Use `@require_role` for endpoints, `can()` for fine-grained checks
2. **Engineer data isolation** - Engineers only see own records + NULL legacy data
3. **ADMIN superuser** - ADMIN passes all permission checks automatically
4. **Frontend 403 handling** - Always parse error message, show required roles in modal
5. **authLoading state** - Prevent race conditions during authentication
6. **Test all roles** - Write tests for engineer, security, legal, and admin access
