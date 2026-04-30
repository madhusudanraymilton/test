/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { dynamicApiRegistry } from "../../js/dynamic_api_registry";

/**
 * EndpointPreview
 * ===============
 * Live, reactive preview panel showing the generated endpoint URL plus
 * ready-to-use code snippets in curl, fetch, Python requests, and Axios.
 *
 * All state is derived from props — this component is purely presentational.
 *
 * Props
 * -----
 * endpointPath : str      — e.g. /api/dynamic/sale-order
 * authType     : str      — 'public' | 'api_key' | 'session'
 * methods      : Object   — { allow_get, allow_post, allow_put, allow_delete }
 * selectedFields : Array  — [{ field_name, alias, is_readonly, field_type }]
 */
export class EndpointPreview extends Component {
    static template = "dynamic_rest_api.EndpointPreview";
    static props = {
        endpointPath: { type: String, optional: true },
        authType: { type: String, optional: true },
        methods: { type: Object, optional: true },
        selectedFields: { type: Array, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({ activeTab: 'curl' });
    }

    // ── Derived ───────────────────────────────────────────────────────

    get fullUrl() {
        if (!this.props.endpointPath) return '';
        return dynamicApiRegistry.getEndpointUrl(this.props.endpointPath);
    }

    get activeMethods() {
        const m = this.props.methods || {};
        const out = [];
        if (m.allow_get)    out.push('GET');
        if (m.allow_post)   out.push('POST');
        if (m.allow_put)    out.push('PUT');
        if (m.allow_delete) out.push('DELETE');
        return out;
    }

    get authHeader() {
        return this.props.authType === 'api_key'
            ? '-H "X-API-Key: YOUR_API_KEY_HERE"'
            : '';
    }

    get authHeaderInline() {
        return this.props.authType === 'api_key'
            ? '"X-API-Key": "YOUR_API_KEY_HERE"'
            : '';
    }

    get paramTable() {
        const fields = this.props.selectedFields || [];
        return fields.map(f => ({
            key: f.alias || f.field_name,
            type: f.field_type,
            readonly: f.is_readonly,
        }));
    }

    // ── Code generators ───────────────────────────────────────────────

    get curlGet() {
        const auth = this.authHeader ? ` \\\n  ${this.authHeader}` : '';
        return `curl -X GET "${this.fullUrl}?page=1&page_size=20"${auth}`;
    }

    get curlPost() {
        const body = this._sampleBody(false);
        const auth = this.authHeader ? ` \\\n  ${this.authHeader}` : '';
        return `curl -X POST "${this.fullUrl}" \\
  -H "Content-Type: application/json"${auth} \\
  -d '${JSON.stringify(body, null, 2)}'`;
    }

    get fetchGet() {
        const headers = this.props.authType === 'api_key'
            ? `\n    "X-API-Key": "YOUR_API_KEY_HERE",` : '';
        return `const response = await fetch(
  "${this.fullUrl}?page=1&page_size=20",
  {
    method: "GET",
    headers: {${headers}
      "Content-Type": "application/json",
    },
  }
);
const { success, data, meta } = await response.json();
console.log(data);`;
    }

    get fetchPost() {
        const body = this._sampleBody(false);
        const headers = this.props.authType === 'api_key'
            ? `\n    "X-API-Key": "YOUR_API_KEY_HERE",` : '';
        return `const response = await fetch(
  "${this.fullUrl}",
  {
    method: "POST",
    headers: {${headers}
      "Content-Type": "application/json",
    },
    body: JSON.stringify(${JSON.stringify(body, null, 2)}),
  }
);
const { success, data } = await response.json();`;
    }

    get pythonGet() {
        const authLine = this.props.authType === 'api_key'
            ? `\nheaders = {"X-API-Key": "YOUR_API_KEY_HERE"}` : '\nheaders = {}';
        return `import requests
${authLine}

response = requests.get(
    "${this.fullUrl}",
    params={"page": 1, "page_size": 20},
    headers=headers,
)
data = response.json()
print(data["data"])`;
    }

    get axiosGet() {
        const authLine = this.props.authType === 'api_key'
            ? `\n  headers: { "X-API-Key": "YOUR_API_KEY_HERE" },` : '';
        return `import axios from "axios";

const { data } = await axios.get("${this.fullUrl}", {
  params: { page: 1, page_size: 20 },${authLine}
});
console.log(data.data);`;
    }

    get activeCode() {
        switch (this.state.activeTab) {
            case 'curl':   return this.curlGet;
            case 'post':   return this.curlPost;
            case 'fetch':  return this.fetchGet;
            case 'python': return this.pythonGet;
            case 'axios':  return this.axiosGet;
            default:       return '';
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────

    _sampleBody(includeReadonly) {
        const fields = (this.props.selectedFields || [])
            .filter(f => includeReadonly || !f.is_readonly);
        const body = {};
        for (const f of fields) {
            const key = f.alias || f.field_name;
            body[key] = this._sampleValue(f.field_type);
        }
        return body;
    }

    _sampleValue(ttype) {
        const samples = {
            char: 'value',
            text: 'Long text value',
            integer: 1,
            float: 1.5,
            boolean: true,
            date: '2024-01-15',
            datetime: '2024-01-15 10:00:00',
            many2one: 1,
            selection: 'option_key',
        };
        return samples[ttype] ?? 'value';
    }

    // ── Copy to clipboard ─────────────────────────────────────────────

    async copyCode() {
        try {
            await navigator.clipboard.writeText(this.activeCode);
            this.notification.add('Copied to clipboard!', { type: 'info', sticky: false });
        } catch {
            // Fallback for non-HTTPS or older browsers
            const ta = document.createElement('textarea');
            ta.value = this.activeCode;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            this.notification.add('Copied!', { type: 'info', sticky: false });
        }
    }

    async copyUrl() {
        try {
            await navigator.clipboard.writeText(this.fullUrl);
            this.notification.add('URL copied!', { type: 'info', sticky: false });
        } catch { /* silent */ }
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }
}
