const assert = require('node:assert/strict');
const {identity, validateRows} = require('../app/static/main_v2/js/gtin_position.js');
const rows = [
    {size: '42', size_type: 'РОССИЯ', gtin: '04640735105562', company: 'g:GRENADA'},
    {size: '44', size_type: 'РОССИЯ', gtin: '04640735105579', company: 'g:GRENADA'},
    {size: '46', size_type: 'РОССИЯ', gtin: '', company: ''},
];
assert.deepEqual(validateRows(rows), ['', '', '']);
assert.deepEqual(validateRows(rows.map((row, index) => index === 1 ? {...row, company: 'g:AVRORA'} : row)), ['', '', '']);
assert.match(validateRows([{...rows[0], company: ''}])[0], /вместе/);
assert.match(validateRows([{...rows[0], gtin: ''}])[0], /вместе/);
assert.match(validateRows([{...rows[0], gtin: '123'}])[0], /14 цифр/);
assert.match(validateRows([rows[0], {...rows[1], gtin: rows[0].gtin}])[1], /разные GTIN/);
assert.equal(identity({...rows[0], quantity: 99}), identity(rows[0]));
assert.notEqual(identity(rows[0]), identity({...rows[0], size_type: 'МЕЖДУНАРОДНЫЙ'}));
assert.notEqual(identity({size: '100*200', unit: 'см'}), identity({size: '100*200', unit: 'мм'}));
console.log('GTIN per-size validation and stable identities OK');
