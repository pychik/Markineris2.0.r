import json
from pathlib import Path
import shutil
import subprocess
import unittest

from app.utilities.clothes_tnved_content import (
    LEATHER_TNVED_CONTENT_ERROR,
    LEATHER_TNVED_CONTENT_RULE,
    clothes_tnved_content_error,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("4203100001", "Кожа", True),
    ("4203100009", "нАтУрАлЬнАя кОжА", True),
    ("4203299000", "КОМПОЗИЦИОННАЯ КОЖА", True),
    ("4203100001", "100% кожа", True),
    ("4203100001", "КОЖА 50%, ХЛОПОК 50%", True),
    ("4203100001", "99,5% хлопок; 0,5% натуральная кожа", True),
    ("4203100001", "ХЛОПОК,НАТУРАЛЬНАЯ   КОЖА", True),
    ("4203100001", "100% искусственная кожа", False),
    ("4203100001", "ЭКОКОЖА", False),
    ("4203100001", "ЗАМША", False),
    ("4203100001", "ХЛОПОК", False),
    ("4203100001", "", False),
    ("4203100001", None, False),
    ("4203100001", "КОЖАНЫЙ", False),
    ("6201900000", "100% хлопок", True),
    ("6201900000", "100% кожа", True),
    ("", None, True),
]


class ClothesTnvedContentTests(unittest.TestCase):
    def test_materials_and_other_prefixes(self):
        for code, content, allowed in CASES:
            with self.subTest(code=code, content=content):
                expected = None if allowed else LEATHER_TNVED_CONTENT_ERROR
                self.assertEqual(clothes_tnved_content_error(code, content), expected)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for browser rule tests")
    def test_browser_uses_same_rule_and_clears_code_after_edit(self):
        script = r"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const {rule, cases} = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = {
    clothesTnvedContentRule: {textContent: JSON.stringify(rule)},
    content: {id: 'content', value: 'Кожа'},
    tnved_code: {id: 'tnved_code', value: '4203100001'},
    check_tnved_flag: {value: 'true'},
    tnved_valid_feedback: {textContent: 'OK'},
    tnved_nv_feedback: {textContent: ''}
};
const listeners = {};
const context = {
    window: {},
    document: {
        getElementById: id => elements[id] || null,
        addEventListener: (name, callback) => { listeners[name] = callback; }
    },
    show_form_errors: () => {},
    $: () => ({modal: () => {}})
};
vm.runInNewContext(fs.readFileSync('app/static/main_v2/js/categories/clothes_tnved_content.js', 'utf8'), context);
const validator = context.window.ClothesTnvedContent;
for (const [code, content, allowed] of cases) {
    assert.equal(validator.getError(code, content), allowed ? '' : rule.message);
}
listeners.DOMContentLoaded();
assert.equal(elements.tnved_code.value, '4203100001');
elements.content.value = '100% ХЛОПОК';
listeners.input({target: elements.content});
assert.equal(elements.tnved_code.value, '');
assert.equal(elements.check_tnved_flag.value, 'false');
assert.equal(elements.tnved_valid_feedback.textContent, '');
assert.equal(validator.check('4203100001'), false);
elements.tnved_code.value = '6201900000';
listeners.change({target: elements.content});
assert.equal(elements.tnved_code.value, '6201900000');
assert.equal(elements.tnved_nv_feedback.textContent, '');
elements.tnved_code.value = '4203100001';
listeners.DOMContentLoaded();
assert.equal(elements.tnved_code.value, '');
// Shared category scripts must also work on pages without this rule.
for (const file of ['app/static/main_v2/js/categories/clothes.js', 'app/static/product_cards/users/clothes.js']) {
    const source = fs.readFileSync(file, 'utf8');
    const addContent = source.slice(source.indexOf('function clothes_content_add()'), source.indexOf('function check_nat_content('));
    const fields = {multi_content: {value: 'КОЖА'}, content: {value: 'ХЛОПОК', maxLength: 100}};
    const page = {window: {}, document: {getElementById: id => fields[id]}};
    vm.runInNewContext(addContent, page);
    page.clothes_content_add();
    assert.equal(fields.content.value, 'ХЛОПОК, КОЖА');
}
"""
        subprocess.run(
            ["node", "-e", script],
            input=json.dumps({"rule": LEATHER_TNVED_CONTENT_RULE, "cases": CASES}),
            text=True,
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
