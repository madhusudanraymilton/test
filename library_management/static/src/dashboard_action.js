import { registry } from '@web/core/registry';
import { CustomDashboard } from './dashboard';

registry.category('actions').add('custom_dashboard', CustomDashboard);