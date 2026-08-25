# Интеграция с LiteMark — автоматизированная обработка заказов

Ветка: `feature/litemark-orders-crm`
Внешний контракт (документ для команды LiteMark): [`../integration_guide.md`](../integration_guide.md)

---

## 1. Зачем это нужно

Заказы клиентов, которые раньше руками разбирали операторы CRM, теперь уходят во внешний сервис
LiteMark и обрабатываются там автоматически. Markineris в этой схеме — **сервер**: LiteMark сам ходит
к нам за работой, мы ничего никуда не пушим.

Роли поменялись местами относительно обычной CRM:

- **Markineris** отдаёт заказы, принимает подтверждения/статусы/результат, ведёт аудит.
- **LiteMark** опрашивает нас (polling), обрабатывает, кладёт результат в MinIO, отчитывается.
- **Операторы CRM** больше не берут такие заказы в работу вручную. Отдельная доска
  «Автоматизированные заказы» нужна только чтобы наблюдать за потоком и разруливать проблемные заказы.

---

## 2. Как заказ становится «автоматизированным»

Признак — один флаг на заказе:

```
is_automated_crm IS TRUE
```

Вычисляется одной функцией — [`resolve_automated_crm_flag()`](../app/utilities/support.py):

```python
def resolve_automated_crm_flag(order_comment) -> bool:
    return not (order_comment or '').strip()
```

**Правило: заказ БЕЗ комментария пользователя → автоматизированный, уходит в LiteMark.**
Комментарий — это признак «особенного» заказа: такой разбирает живой оператор обычной CRM.

Комментарий пользователь вводит в модалке оформления заказа, поле «Комментарий к заказу»
(необязательное). Поэтому флаг считается **не при создании заказа, а при отправке** — на момент
создания комментария ещё нет ни в одном из потоков.

Проставляется в одном месте — [`process_order_start()`](../app/utilities/support.py), там же, где
пишется `order.user_comment`:

```python
order.user_comment = order_comment
order.is_automated_crm = resolve_automated_crm_flag(order_comment)
```

Это единственная общая точка всех потоков создания заказа: обычная форма категории, загрузка
из Excel (создаёт черновик, который отправляется тем же путём) и заказы из карточек товаров.
Отдельных мест простановки флага больше нет.

> ### ⚠️ Пересмотреть после включения «Быстрого заказа»
>
> Сейчас раздел **«Быстрый заказ»** (карточки товаров, blueprint `user_product_cards`) полностью
> отключён гардом [`product_cards_maintenance_guard`](../app/views/main/product_cards/users.py):
> GET уходит в редирект, остальное отдаёт 503. Поэтому `is_moderation` больше никому не
> проставляется — все новые заказы обычные.
>
> Из-за этого признак автоматизации сведён к одному `is_automated_crm`, а `is_moderation`
> из всех отборов убран. Раньше правило было «модерационный заказ без комментария».
>
> **Включение «Быстрого заказа» планируется после октября 2026.** Когда его вернут, правило
> определения автоматического заказа нужно пересмотреть: скорее всего понадобится снова
> различать быстрые и обычные заказы, а сейчас они не различаются вообще.
>
> Что придётся перепроверить:
>
> - `resolve_automated_crm_flag()` — нужен ли обратно параметр `is_moderation`;
> - `_external_processing_order_filter()` в [`integration_service.py`](../app/views/api/integration_service.py);
> - `AUTOMATED_ORDER_FILTER_SQL`, `_automated_order_expr()` в [`crm_automated/service.py`](../app/views/crm_automated/service.py);
> - `LEGACY_CRM_ORDER_FILTER_SQL` в [`crm/helpers.py`](../app/views/crm/helpers.py);
> - частичный индекс `ix_orders_external_claim_queue` — условие придётся менять снова, миграцией;
> - `h_make_pc_basket_order()` ставит `is_automated_crm=True` при создании — с включённым
>   разделом это значение перезапишется на отправке, но проверить стоит.

### Разделение потоков

Чтобы автоматизированные заказы не попадали в старую CRM, во все legacy-выборки добавлен фильтр
[`LEGACY_CRM_ORDER_FILTER_SQL`](../app/views/crm/helpers.py):

```sql
AND o.is_automated_crm IS NOT TRUE
```

Затронуты: `helper_get_agent_orders`, `helper_get_agent_stage_orders`, `helper_get_manager_orders`
(две ветки), `get_weekly_order_summary`.

### Существующие заказы

Заказы, созданные до этого изменения, **намеренно не переводятся** в автоматизированные — у них
`is_automated_crm = false`, и они остаются в обычной CRM. Правило применяется только к новым.

CLI `backfill_is_automated_crm` оставлен как ручной инструмент на случай, если решение изменится;
сам по себе он не запускается и в деплой не входит.

---

## 3. Схема данных

### Новая таблица `external_processors`

Одна строка = один внешний обработчик (LiteMark — первый и пока единственный).
Модель: [`app/models.py`](../app/models.py).

| Поле | Назначение |
|---|---|
| `name` | человекочитаемое имя, уникально |
| `key_id` | публичный идентификатор, приходит в `X-Integration-Key-Id`, уникален |
| `shared_secret` | секрет для подписи (хранится **в открытом виде**) |
| `allowed_ips` | CSV-список разрешённых IP; пусто = проверка выключена |
| `minio_bucket_name` | бакет, куда обработчик кладёт результат |
| `minio_prefix` | префикс `object_key` (например `incoming`) |
| `ttl_seconds` | допустимый разбег `X-Integration-Timestamp`, по умолчанию 300 |
| `nonce_ttl_seconds` | сколько помним nonce, по умолчанию 600 |
| `batch_size` | размер пачки в `GET /orders`, по умолчанию 10 |
| `confirmation_timeout_seconds` | таймаут подтверждения И обработки, по умолчанию 300 |
| `source_label` | попадает в `orders.stage_setter_name` и в логи; уникален |
| `is_active` | выключатель |

Дефолты — в [`app/external_processors/config.py`](../app/external_processors/config.py).

### Новая таблица `order_processed_logs`

Аудит всего, что происходит с заказом во внешней обработке. Пишется через `log_order_event()`.

Поля: `order_id`, `event_type`, `status`, `dispatch_token`, `stage`, `message`, `object_key`,
`source`, `payload` (JSONB), `created_at`.

Значения `event_type`:

**Внешний обработчик**

| event_type | Когда |
|---|---|
| `claimed` | заказ выдан обработчику |
| `accepted` | обработчик прислал `accept` |
| `status_updated` | промежуточный статус |
| `result_processed` | успешный финальный результат |
| `result_failed` | неуспешный результат |
| `result_missing_upd_number` | в `result` не пришёл `upd_number` |
| `result_invalid_payload` | в `result` не пришёл `object_key` |
| `result_invalid_object_key` | `object_key` не совпал с выданным |
| `result_missing_object` | файла нет в MinIO |
| `problem_ack` | обработчик подтвердил снятие заказа по таймауту |

**Система**

| event_type | Когда |
|---|---|
| `prevalidated` | заказ прошёл превалидацию, закреплена компания, заказ переведён из «Новых» в пул |
| `prevalidation_failed` | превалидация не прошла, заказ ушёл оператору |
| `claim_failed_missing_source` | не удалось собрать исходный zip |
| `claim_expired` | обработчик не подтвердил выдачу — заказ вернулся в пул |
| `processor_timeout` | истёк таймаут обработки — заказ снят и передан оператору |

**Оператор CRM**

| event_type | Когда |
|---|---|
| `operator_take` | взял заказ в работу |
| `operator_problem` | перевёл в проблему |
| `operator_back_to_work` | вернул из проблемы в работу |
| `operator_processed` | закрыл как обработанный |
| `operator_stage_change` | перевёл между стадиями |
| `operator_cancelled` | отменил заказ |
| `operator_upd_set` | проставил компанию и номер УПД |

В поле `source` у событий оператора стоит его `login_name`, у внешних — `source_label`
обработчика, у системных — `external_processor`. Всё это видно на вкладке «Логи» вместе
с сырым `payload` каждого события.

Запись аудита обёрнута в `try/except`: сбой логирования не ломает действие оператора.

### Границы доверия и лимиты

- **`upd_number` экранируется.** Приходит от внешнего сервиса, а `processing_info` рендерится
  в шаблонах через `| safe` — без экранирования это хранимая XSS. `build_processing_info()`
  прогоняет значения через `markupsafe.escape`, разметка карточки (`<br>`) остаётся живой.
- **Длина `upd_number` проверяется до записи** (`UPD_NUMBER_MAX_LENGTH = 100`). Более длинный
  номер уронил бы вставку на `StringDataRightTruncation` и потерял бы весь финальный результат;
  вместо этого заказ уходит в проблему с событием `result_invalid_upd_number`.
- **`/orders/problems` и `/problem-ack` ограничены своим обработчиком** по `stage_setter_name`.
  Без этого второй подключённый обработчик получал бы чужие заказы вместе с их dispatch-токенами.

### Что пишется в технический лог, а не в БД

Часть событий не привязана к заказу и в `order_processed_logs` попасть не может:

- **любой отказ webhook-а** — `_error()` пишет `code`, HTTP-статус, `key_id`, IP, метод и путь.
  Без этого разбор «почему у партнёра не проходит запрос» упирается в пустоту: заказа ещё нет,
  а отказы по подписи, nonce, rate limit и IP нигде не оставались;
- **отклонённые заказы в `accept`** — `order_id` и причина;
- **факт выдачи проблемного списка** — какие `order_id` отданы обработчику. В БД остаются
  только границы: `processor_timeout` при снятии и `problem_ack` при подтверждении.

### Изменения в `orders`

| Поле | Назначение |
|---|---|
| `is_automated_crm` | флаг из п. 2 |
| `status` | внешний статус (`delivery_unconfirmed`, `accepted`, `in_progress`, `processed`, …) |
| `dispatch_token` | токен конкретной выдачи |
| `object_key` | путь в MinIO, куда обработчик должен положить результат |
| `confirmed_at` | момент подтверждения обработчиком |

Частичный индекс под очередь выдачи:

```sql
ix_orders_external_claim_queue (crm_created_at, id)
WHERE stage = 2 AND is_moderation IS TRUE AND is_automated_crm IS TRUE AND to_delete IS NOT TRUE
```

Дополнительно: `order_files.file_link` расширен со `String(100)` до `String(512)`.

---

## 4. Webhook API

Blueprint `api` зарегистрирован с префиксом `/api`, роуты — `/webhook/...`, итого база: **`/api/webhook`**.

Код: [`app/views/api/integrations.py`](../app/views/api/integrations.py) (HTTP-слой, аутентификация)
и [`app/views/api/integration_service.py`](../app/views/api/integration_service.py) (бизнес-логика).

| Метод | Путь | Функция |
|---|---|---|
| `GET` | `/api/webhook/orders` | `api_claim_orders` |
| `POST` | `/api/webhook/orders/accept` | `api_accept_orders` |
| `POST` | `/api/webhook/orders/<order_id>/status` | `api_update_order_status` |
| `POST` | `/api/webhook/orders/<order_id>/result` | `api_update_order_result` |

Все четыре освобождены от CSRF в [`initialization.py`](../app/settings/initialization.py).

### Порядок проверок в `_resolve_processor_request()`

1. наличие всех четырёх заголовков → `missing_headers` (401)
2. поиск активного обработчика по `key_id` → `unknown_key_id` (403) / `integration_not_configured` (500)
3. парсинг `timestamp` → `invalid_timestamp` (400)
4. `|now - timestamp| > ttl_seconds` → `expired_timestamp` (401)
5. IP-allowlist → `ip_not_allowed` (403)
6. подпись → `invalid_signature` (401)
7. nonce (Redis `SET NX EX`) → `replay_nonce` (409)
8. rate limit 50 req/min на `key_id` → `rate_limited` (429)

Ключи Redis: `external-processing:nonce:{key_id}:{nonce}`,
`external-processing:ratelimit:{key_id}:{minute}`.

### Жизненный цикл заказа

```
                    POOL (2)
                       │
        GET /orders    │  claim_new_orders()
                       ▼
              MANAGER_START (3)
              status=delivery_unconfirmed
              dispatch_token, object_key, sent_at
                       │
      ┌────────────────┼─────────────────────────┐
      │                │                         │
  нет accept       accept /              result: processed
  дольше timeout   status                (+ файл есть в MinIO)
      │                │                         │
      ▼                ▼                         ▼
  POOL (2)      confirmed_at=now         CRM_PROCESSED (11)
  claim_expired  status=accepted          processed=True
                       │                  closed_at=now
                 нет result дольше
                 timeout ──────────► MANAGER_PROBLEM (6)
                                     external_problem=True
                 result: failed/problem/error ──┘
```

### `GET /orders` — выдача

`claim_new_orders()`:

1. вызывает `requeue_expired_unconfirmed_orders()` и `mark_stale_processing_orders_as_problem()`
   (**inline, отдельного планировщика нет** — см. п. 8);
2. берёт `batch_size + 1` заказов из пула с `FOR UPDATE SKIP LOCKED`, сортировка
   `crm_created_at ASC, id ASC`; лишний заказ нужен только чтобы посчитать `has_more`;
3. для каждого собирает исходный zip через `get_order_download_payload()` — при неудаче заказ
   уходит в проблему с `claim_failed_missing_source` и не выдаётся;
4. генерирует `dispatch_token = uuid4().hex` и `object_key`;
5. переводит заказ в `MANAGER_START` со статусом `delivery_unconfirmed`.

`object_key` строится в `create_object_key()`:

```
{minio_prefix}/{order_id}/{dispatch_token}/result.zip
```

**`processing_company` выбирается случайно** (`random.choice`) из подтверждённых активных компаний
пользователя (`UserProcessingCompany.is_approved AND ProcessingCompany.is_active`). Это осознанное
бизнес-правило — распределение нагрузки между компаниями обработки, а не баг.

Заголовки ответа: `X-Orders-Returned`, `X-Orders-Limit-Applied`, `X-Orders-Has-More`,
`X-Orders-Remaining` (см. расхождение №3).

### `POST /orders/accept`

Пакетный. Требует `order_id`, `dispatch_token`, `status == 'accepted'`. Заказ должен быть
в стадии `MANAGER_START`. Идемпотентен: повторный accept не перезатирает `confirmed_at`.
Ответ: `{"accepted": [...], "rejected": [{"order_id":..., "reason":...}]}` — всегда HTTP 200.

### `POST /orders/{id}/status`

Требует `dispatch_token` и непустой `status`. Финальные статусы (`processed`, `failed`, `problem`,
`error`) здесь **запрещены**. Если `accept` не приходил — первый валидный `status` сам проставляет
`confirmed_at` (как и обещано в гайде).

### `POST /orders/{id}/result`

Разрешённые стадии: `MANAGER_START`, `MANAGER_PROBLEM`, `CRM_PROCESSED` — то есть поздний результат
долетит, даже если оператор уже утащил заказ в проблему.

При `status == 'processed'` проверяется три вещи: `object_key` пришёл, совпадает с выданным,
и объект реально есть в бакете (`S3Service.object_exists()`). Любая из проверок не прошла →
заказ помечается проблемным. **Ответ при этом — HTTP 200**, см. расхождение №4.

Остальные статусы (`failed`/`problem`/`error`) → `MANAGER_PROBLEM`, `external_problem=True`,
`message` обрезается до 230 символов в `comment_problem`.

---

## 5. Расхождения кода и внешнего контракта

> Это главный раздел документа. Гайд у LiteMark на руках; ниже — где реализация от него отходит.
> Часть расхождений сделана намеренно (№1), часть требует правки кода, часть — правки гайда.

### ✅ №1. Подпись упрощена намеренно — под ограничения 1С

**Это согласованное решение, а не дефект.** Реализация сознательно отличается от того, что описано
в гайде, и код здесь — источник истины.

Изначально в гайд заложили HMAC-SHA256 по канонической строке из шести частей:

```
{key_id}\n{timestamp}\n{nonce}\n{METHOD}\n{request_path}\n{sha256_hex(body)}
```

Сторона LiteMark работает на 1С, где нет штатных средств для HMAC, и корректно посчитать подпись
не получилось. По итогам обсуждения с их командой договорились на схему, которая опирается только
на голый SHA-256 — его 1С умеет надёжно:

```
sha256(shared_secret + "\n" + timestamp + "\n" + nonce)
```

Именно это и делает [`_sha256_signature()`](../app/views/api/integrations.py):

```python
def _sha256_signature(shared_secret: str, timestamp: str, nonce: str) -> str:
    signature_bytes = b'\n'.join([
        shared_secret.encode('utf-8'),
        timestamp.encode('utf-8'),
        nonce.encode('utf-8'),
    ])
    return hashlib.sha256(signature_bytes).hexdigest()
```

Что схема даёт: подтверждение владения секретом (аутентификация клиента), защиту от повтора за счёт
одноразового `nonce` и ограничение окна за счёт `timestamp` + `ttl_seconds`. Для задачи «понять,
что запрос от доверенного клиента» этого достаточно.

**Чего схема не даёт** — принимается осознанно:

- тело запроса не входит в подпись, целостность body держится на TLS;
- метод и путь не связаны с подписью: в пределах `ttl_seconds` одна подпись формально подходит
  к любой из четырёх ручек (переиспользовать её нельзя — гасит `nonce`);
- конструкция `sha256(secret || data)` слабее HMAC по построению; при фиксированной длине секрета
  length-extension здесь напрямую не эксплуатируется.

На практике всё перечисленное требует активной позиции на канале, которую закрывает HTTPS,
и дополняется IP-allowlist (когда он заработает, см. №2).

**Что действительно нужно сделать: привести гайд в соответствие.**
Раздел `Формальная спецификация подписи` в [`integration_guide.md`](../integration_guide.md)
по-прежнему описывает HMAC с шестичастной канонической строкой и содержит Python-примеры под неё.
Договорённость зафиксирована только в переписке — у LiteMark на руках документ, противоречащий
и коду, и договорённости. Гайд надо переписать под фактическую схему.

**Опциональное усиление, если понадобится.** Тело можно вернуть в подпись, не вводя HMAC и оставаясь
в рамках возможностей 1С, — добавлением ещё одного элемента в ту же конкатенацию:

```
sha256(secret + "\n" + timestamp + "\n" + nonce + "\n" + sha256(body))
```

Ломает совместимость, поэтому только по согласованию с LiteMark. Отдельно проговорить с ними,
что 1С должна считать хеш ровно от тех байтов, которые реально уходят в сеть.

### ⛔ №2. IP-allowlist не работает за nginx

[`initialization.py:78`](../app/settings/initialization.py):

```python
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
```

`x_for` не задан → по умолчанию `0` → `request.remote_addr` возвращает IP nginx, а не клиента,
хотя nginx корректно проставляет `X-Forwarded-For` и `X-Real-IP`.

Значит, `allowed_ips` в текущем виде:

- пустой — проверка просто выключена;
- заполненный реальными IP LiteMark — **заблокирует все запросы**.

Чинится добавлением `x_for=1` (с учётом числа доверенных прокси). Менять осторожно: `ProxyFix`
глобальный, затронет всё приложение.

### ✅ №3. `X-Orders-Remaining` приходит не всегда — гайд поправлен

Код ([`integrations.py:143`](../app/views/api/integrations.py)) ставит заголовок **только когда
`has_more == false`**, и всегда в значение `'0'`:

```python
if not has_more:
    headers['X-Orders-Remaining'] = '0'
```

Реального остатка мы не считаем — для этого нужен отдельный `COUNT`.

Гайд раньше показывал `X-Orders-Remaining: 7` вместе с `X-Orders-Has-More: true`, то есть обещал
счётчик очереди, которого нет. **Исправлено:** в гайде теперь два примера ответа (пул не пуст /
пул исчерпан), явно сказано, что `X-Orders-Remaining` приходит только с `has_more: false` и всегда
равен `0`, и что опираться в polling-цикле надо на `X-Orders-Has-More`.

Если позже понадобится честный остаток — `count_available_orders()` уже написана
([`integration_service.py`](../app/views/api/integration_service.py)) и сейчас не используется.

### ⚠️ №4. Ошибки `result` возвращаются как HTTP 200

В `apply_result_update()` три ветки — нет `object_key`, `object_key` не совпал, файла нет в MinIO —
помечают заказ проблемным и возвращают `(True, 'problem')`, то есть **HTTP 200** с телом
`{"status":"ok", "data":{"status":"problem"}}`.

Из-за этого коды `object_key_mismatch`, `uploaded_object_not_found` и соответствующий
`invalid_payload` из `code_map` в [`integrations.py:222`](../app/views/api/integrations.py)
**недостижимы** — обещаны в гайде, но никогда не отдаются.

LiteMark по гайду ждёт 400 и код ошибки, а получит 200 OK и будет считать, что всё хорошо.
Нужно определиться: либо возвращать 400 (тогда заказ всё равно надо пометить проблемным),
либо описать в гайде, что признак неуспеха — `data.status == "problem"` при HTTP 200.

### ✅ №5. `replay_nonce` не описан в гайде — добавлен

Код отдаёт `409 replay_nonce`, в списке кодов гайда его не было. **Исправлено:** код добавлен
в список, плюс пояснение — причина почти всегда на стороне клиента (переиспользование nonce
при retry), и повторять запрос без нового `nonce`/`timestamp` и пересчёта подписи бессмысленно.

Там же добавлены технические 500-е: `claim_failed`, `accept_failed`, `status_update_failed`,
`result_update_failed` — с пометкой, что это сбой Markineris, а не отказ по содержанию запроса,
и такой запрос можно безопасно повторить позже.

### ✅ №6. Внутреннее противоречие в самом гайде — устранено

В основном разделе гайда была ручка `POST {BASE_URL}/orders/accept` (пакетная), а в чек-листе
dev-стенда — `POST /api/webhook/orders/{order_id}/accept`. Код реализует **пакетный** вариант.

**Исправлено:** пункт 2 чек-листа приведён к пакетной ручке с уточнением, что `order_id`
передаётся в теле запроса.

### ℹ️ №7. Не описано в гайде, но проверяется кодом

- `accept` принимается только со стадии `MANAGER_START`; иначе `invalid dispatch token`;
- `status` со значением из `FINAL_RESULT_STATUSES` отклоняется явно;
- разбег `timestamp` — `ttl_seconds` обработчика (по умолчанию 5 минут, симметрично);
- rate limit — фиксированное минутное окно, а не скользящее: на стыке минут реально пролетает
  до 100 запросов за 60 секунд.

---

## 6. Админка: управление внешними обработчиками

Доступ: только `superuser`. Вход — `Админ-панель → Внешние обработчики`.

Страница: [`admin_control.external_processors_main`](../app/views/main/admin_control.py) →
`admin/external_processors/main.html`.

CRUD-API (blueprint `external_processors_admin`, префикс `/admin_control`):

| Метод | Путь |
|---|---|
| `GET` | `/admin_control/external_processors` |
| `GET` | `/admin_control/external_processors/<id>` |
| `POST` | `/admin_control/external_processors` |
| `PUT` | `/admin_control/external_processors/<id>` |
| `DELETE` | `/admin_control/external_processors/<id>` |

Валидация — pydantic-схемы [`ExternalProcessorCreateSchema` / `UpdateSchema`](../app/external_processors/schemas.py).
`key_id` и `shared_secret` можно не передавать — сгенерируются (`secrets.token_hex(8)` и
`token_hex(32)`). `source_label` автоматически делается уникальным (`-2`, `-3`, …).

`shared_secret` отдаётся наружу в ответах на detail/create/update (`include_secret=True`) — это
нужно, чтобы админ мог передать секрет LiteMark, но означает, что секрет живёт в БД в открытом виде.

---

## 7. CRM «Автоматизированные заказы»

Отдельная доска, чтобы автоматизированный поток не смешивался с обычной CRM.

Доступ: `superuser` и `supermanager` (`su_sm_required`).
URL: `/crm_automated_orders/orders`. Ссылки — в шапке (`base_header.html`) и в `user_tab.html`.

Код: [`dashboard.py`](../app/views/crm_automated/dashboard.py) (роуты, тонкий слой) и
[`service.py`](../app/views/crm_automated/service.py) (~1460 строк логики).
Шаблоны — `app/templates/crm_automated_v1/`, скрипты — `app/static/crm_mod/js/crm_automated.js`.

Колонки доски:

| Стадия | Название |
|---|---|
| `POOL` (2) | Пул |
| `MANAGER_START` (3) | В обработке |
| `MANAGER_PROBLEM` (6) | Проблема в заказе |
| `CRM_PROCESSED` (11) | Обработано |
| `CANCELLED` (9) | Отменено |

Что умеет оператор: взять заказ, перевести в проблему, вернуть в работу, обработать, отменить
(только из проблемы), двигать по стадиям, работать с файлами и чатом заказа, смотреть карточку.

Две вкладки специально под интеграцию:

- **Техническая информация** — `dispatch_token`, `object_key`, `confirmed_at`, `stage_setter_name`
  и цветной бейдж внешнего статуса (`_build_external_status_meta()`);
- **Логи** — вся история из `order_processed_logs`, включая сырой `payload` каждого события.

---

## 8. Таймауты и «зависшие» заказы

Два механизма, оба в [`integration_service.py`](../app/views/api/integration_service.py):

| Функция | Условие | Результат |
|---|---|---|
| `requeue_expired_unconfirmed_orders()` | `MANAGER_START` + `delivery_unconfirmed` + нет `confirmed_at` + `sent_at` старше таймаута | обратно в `POOL`, токен и `object_key` очищены, событие `claim_expired` |
| `mark_stale_processing_orders_as_problem()` | `MANAGER_START` + `confirmed_at` старше таймаута | в `MANAGER_PROBLEM`, событие `processor_timeout` |

### Три проблемы этой схемы

**1. Обе функции вызываются только из `claim_new_orders()`.** Отдельной задачи в
`app/redis_queue/scheduler.py` нет. Если LiteMark перестанет опрашивать `GET /orders` — а это ровно
тот сценарий, ради которого таймауты и нужны, — зависшие заказы не разберёт никто.

**2. Один параметр на два разных таймаута.** `confirmation_timeout_seconds` (по умолчанию **300 с**)
означает и «сколько ждём accept», и «сколько ждём финальный result». Пять минут на подтверждение —
разумно; пять минут на всю обработку заказа — почти наверняка нет. При текущем дефолте любой заказ,
который LiteMark обрабатывает дольше пяти минут, уедет в проблему. Нужны два независимых параметра.

> **Решено на созвоне 18.08.2026:** таймаут обработки — **2 суток** (172 800 с), после чего заказ
> уходит в проблему, а LiteMark об этом уведомляется и должен подтвердить смену статуса.
> Подробности и что это меняет — в разделе 11.

**3. Порог в UI не совпадает с бэкендом.** `AUTOMATED_EXTERNAL_CONFIRMATION_OVERDUE_SECONDS = 3600`
в [`service.py`](../app/views/crm_automated/service.py) рисует красный бейдж «нет подтверждения
более часа». Но бэкенд вернёт заказ в пул уже через 5 минут, так что этот бейдж при дефолтных
настройках не покажется никогда.

---

## 9. MinIO

LiteMark кладёт результат напрямую в MinIO по S3 API — Markineris файл не проксирует.
Для этого нужен отдельный ограниченный пользователь хранилища (upload-only).

Скрипт: [`minio_setup/init_minio_integrations.sh`](../minio_setup/init_minio_integrations.sh).
Конфиг: `minio_setup/minio_integrations.local.conf` (в git не попадает) или `minio_integrations.conf`.
Пример формата — [`minio_integrations.example.conf`](../minio_setup/minio_integrations.example.conf).

```
# name|user|password_or_@file|bucket|prefix|access_mode
litemark|litemark-uploader|@/run/secrets/minio_litemark_password|litemark-results|incoming|upload-only
```

Режимы: `upload-only` (только `PutObject`, читать нельзя), `readonly`, `readwrite`.
Скрипт создаёт бакет, заводит пользователя, генерирует и прикрепляет policy.

Проверку наличия загруженного файла делает `S3Service.object_exists()` в
[`minio_service/services.py`](../app/utilities/minio_service/services.py).

> **Скрипт нигде не подключён.** `docker-compose-minio.yml` его не вызывает (сервис `create_buckets`
> создаёт только `crm`, `bill` и `static`). Запускать вручную в контейнере с `mc`, где уже настроен
> alias `s3`. Стоит либо добавить шаг в compose, либо описать запуск в деплой-инструкции.

---

## 10. Локальный эмулятор LiteMark

[`dev/litemark_emulator.py`](../dev/litemark_emulator.py) ходит в Markineris ровно так, как будет
ходить их сервис: та же подпись, те же шесть ручек. Нужен, чтобы прогнать цикл заказа
и посмотреть на поведение CRM, не дожидаясь их реализации.

HTTP на stdlib, зависимостей нет. `minio` подтягивается лениво и только для загрузки результата —
без него доступно всё, кроме успешного финала.

```bash
export LITEMARK_BASE_URL=https://<dev-стенд>/api/webhook
export LITEMARK_KEY_ID=<key_id из админки>
export LITEMARK_SECRET=<shared_secret из админки>
export MINIO_ENDPOINT=<корень S3>
export MINIO_ACCESS_KEY=<upload-only пользователь>
export MINIO_SECRET_KEY=<его пароль>

python3 dev/litemark_emulator.py selftest    # сверить подпись с векторами из ТЗ
python3 dev/litemark_emulator.py poll        # посмотреть, что отдаёт пул, ничего не трогая
python3 dev/litemark_emulator.py cycle       # claim -> accept -> status -> upload -> result
```

Сценарии:

| Команда | Что проверяет |
|---|---|
| `cycle` | успешный путь целиком, заказ доходит до `CRM_PROCESSED` с номером УПД |
| `cycle --fail` | `result` со статусом ошибки, заказ уходит в проблему с текстом от ЧЗ |
| `cycle --no-accept` | подтверждение не отправляется — через 5 минут заказ вернётся в пул |
| `cycle --limit 1` | взять из пачки только один заказ |
| `problems` | забрать снятые по таймауту обработки и подтвердить через `problem-ack` |
| `problems --no-ack` | только посмотреть список, не подтверждая |

`poll` и `cycle` сохраняют исходный zip в `dev/litemark_incoming/` — можно открыть Excel
и убедиться, что в служебном листе есть строка «Компания обработки».

> **`poll` не безобиден.** `GET /orders` — это выдача: заказ переходит в `MANAGER_START`,
> получает `dispatch_token` и `object_key`. Если после этого не отправить `accept`,
> через `confirmation_timeout` он вернётся в пул уже с другим токеном.

---

## 11. Эксплуатация

### Миграции

Две ревизии: `ebaa1e17f763` (базовая — `external_processors`, новые колонки `orders`) →
`bb01a6438ef2`.

> ⚠️ **`app/migrations/` в `.gitignore`** (`app/.gitignore:131`). Файлы ревизий существуют только
> локально и в git не попадают. На чистом клоне репозитория их нет — накатить схему будет нечем.
> Решить до деплоя: либо снять каталог из ignore, либо зафиксировать порядок доставки миграций
> отдельным способом.

### CLI

```bash
flask backfill_is_automated_crm --dry-run
```

Проставляет `is_automated_crm` историческим модерационным заказам по правилу из п. 2.
Сначала всегда `--dry-run` — он печатает построчный план без записи. Есть `--limit N`.

### Порядок подключения нового обработчика

1. Прогнать миграции.
2. Выполнить `backfill_is_automated_crm` (сначала dry-run).
3. Завести пользователя MinIO через `init_minio_integrations.sh`.
4. Создать обработчика в админке; сохранить `key_id` и `shared_secret`.
5. Передать LiteMark: base URL, `key_id`, `shared_secret`, MinIO endpoint и креды.
6. Собрать внешние IP LiteMark в `allowed_ips` — **только после того, как починен `ProxyFix`**
   (расхождение №2), иначе доступ закроется полностью.
7. Прогнать полный цикл на dev-стенде: `GET /orders` → `accept` → `status` → upload → `result`.

### Диагностика

- **Заказ не выдаётся** — проверить `stage = 2`, оба флага, `to_delete IS NOT TRUE`,
  `is_active` у обработчика.
- **`invalid_signature`** — код считает `sha256(secret\\ntimestamp\\nnonce)`, а гайд всё ещё описывает
  HMAC; убедиться, что клиент делает как в коде (расхождение №1).
- **`ip_not_allowed`** — см. расхождение №2.
- **Заказ ушёл в проблему сам** — событие `processor_timeout` в логах, см. п. 8.
- **Что вообще происходило с заказом** — вкладка «Логи» на доске автоматизированных заказов,
  таблица `order_processed_logs` по `order_id`.

---

## 12. Новые требования (созвон с руководством, 18.08.2026)

Ниже — что изменилось после созвона, и что из этого уже закрыто текущей реализацией, а что нет.

### 11.1. Решения

| Решение | Статус |
|---|---|
| Максимум **2 суток** в обработке, дальше — в проблему; LiteMark уведомить и получить от них подтверждение смены статуса | ⬜ требует доработки |
| Преподготовка: если пользователь не указал РД, подбираем сами через **Тезаурус** перед отправкой в LiteMark | ⬜ требует доработки |
| Любая проблема → статус «проблема» с комментарием, дальше вручную оператором | ✅ есть |
| **УПД отдаёт LiteMark** при успешной обработке | ⬜ требует доработки |
| Заказ с комментарием пользователя → ручная обработка; **выбран вариант с двумя разными CRM** | ✅ есть |
| Из проблемы оператор может добавлять УПД, писать комментарии, двигать стадии | ✅ есть |
| Чаты в заказах остаются | ✅ есть |
| Логи по заказам и просмотр деталей | ✅ есть |

### 11.2. Что уже закрыто — трогать не нужно

- **Две CRM.** Реализовано именно выбранным вариантом: доска `crm_automated` + фильтр
  `LEGACY_CRM_ORDER_FILTER_SQL` в старой CRM (разделы 2 и 7).
- **Проблема → ручной режим.** `_mark_order_problem()` переводит заказ в `MANAGER_PROBLEM`
  с `comment_problem`, дальше он живёт на доске у оператора.
- **Оператор добавляет УПД из проблемы.** Уже есть:
  `update_automated_processing_order_info_response()` принимает компанию и `upd_number`.
  Более того, `process_order()` не даёт закрыть заказ с пустым `processing_info` — то есть без УПД
  заказ не обработать.
- **Чаты, логи, детали** — разделы 3 и 7, вкладки «Логи» и «Техническая информация».

### 11.3. Что проверено и пробелом **не** является

Отдельно, чтобы не заводить лишних задач: всё, что нужно LiteMark по шагам из инструкции
руководителя, **уже уезжает к ним внутри Excel** в `source_file`, а не требует новых полей в JSON.

`excel_add_worksheet_data()` в [`download.py`](../app/utilities/download.py) кладёт на отдельный лист
`company_idn` (ИНН клиента — нужен на шаге 8 для ввода в оборот), `company_name`, `company_type`,
`edo_type`, `edo_id`, `mark_type` (макет/тип маркировки — нужен на шаге 7). В строках позиций уже
есть `ТНВЭД`, `Товарный знак`, `страна` (шаг 5: РФ или импорт) и собранный `declar_doc`.

Расширять `serialize_order_for_api()` под это не требуется.

### 11.4. Таймаут 2 суток + уведомление LiteMark

Самое крупное изменение, потому что **ломает текущую модель взаимодействия**.

Сейчас интеграция чисто **pull**: LiteMark ходит к нам, мы никуда не ходим. Требование «уведомить
LiteMark и получить подтверждение» означает, что кто-то должен инициировать обмен в обратную сторону.

Два варианта, решение нужно зафиксировать с LiteMark:

- **Push (мы становимся клиентом их API).** Нужны их base URL, их схема авторизации, эндпоинт
  и формат подтверждения. Плюс на нашей стороне — исходящие ретраи, таймауты и обработка их
  недоступности. Дороже, и мы начинаем зависеть от их сетевой доступности.
- **Pull (рекомендуется).** Мы помечаем заказ проблемным и отдаём его в новой ручке
  `GET /webhook/orders/problems`; LiteMark забирает список и подтверждает — либо через существующий
  `POST /orders/{id}/status`, либо через отдельный `POST /orders/{id}/problem-ack`. Переиспользует
  готовую инфраструктуру подписи, nonce и rate limit, не требует от нас знать их сеть и не меняет
  роль «LiteMark — клиент».

Что нужно в любом варианте:

1. **Развести таймауты.** Сейчас `confirmation_timeout_seconds` (300 с) отвечает и за accept,
   и за result. Нужен отдельный `processing_timeout_seconds` = `172800`. В колонку он влезает:
   ограничение схемы — `le=604800` ([`schemas.py`](../app/external_processors/schemas.py)).
2. **Планировщик.** Двухсуточный таймер нельзя держать внутри `GET /orders` — см. раздел 8,
   проблема 1. Нужна периодическая задача в `app/redis_queue/scheduler.py`.
3. **Признак «уведомлён / подтверждено»** на заказе, иначе непонятно, дошло ли до LiteMark;
   плюс события в `order_processed_logs` (например `problem_notified` и `problem_ack`).
4. **Согласовать порог бейджа в UI** — `AUTOMATED_EXTERNAL_CONFIRMATION_OVERDUE_SECONDS` (1 час)
   относится к подтверждению выдачи, а не к обработке; для 2 суток нужен свой индикатор.

### 11.5. Преподготовка: подбор РД через Тезаурус

Новый этап **до** попадания заказа в пул выдачи. Пока РД не проставлен, заказ не должен быть
eligible для `claim_new_orders()`.

Где лежит РД: на позициях, в `CommonMixin` ([`models.py`](../app/models.py)) — `rd_type`, `rd_name`,
`rd_date`, `rd_date_to`. «Пользователь не ввёл РД» = эти поля пусты у позиций заказа.

Критерии подбора (их применяет Тезаурус у себя, нам нужно только корректно отдать исходные данные):

1. в РД должен быть **чётко прописан товар** (например, «туфли женские из натуральной кожи»);
2. важны **возраст** (детские/взрослые) и **первые четыре цифры ТНВЭД** — полное совпадение кода
   не требуется;
3. **товарный знак** должен либо совпадать с указанным в РД, либо отсутствовать в РД — иначе
   «Честный Знак» забракует модерацию.

Что учесть:

- РД не подобрался → заказ в проблему с внятным комментарием, дальше руками (это же правило
  из п. 11.1).
- Если РД указан клиентом — **не трогаем**, оставляем как есть.
- Модуль [`app/tezaurus/`](../app/tezaurus/) уже есть, но сейчас это Redis-кэш словарей
  (цвета, страны); подбора РД в нём нет — понадобится новый метод/эндпоинт на стороне Тезауруса.
- Смежно: [`app/fsa/`](../app/fsa/) уже умеет **проверять** РД в госреестре
  (`check_rd(doc_type, number, tnved_code, country)`) и содержит готовые лимитер, circuit breaker
  и последовательную очередь. Подбор (Тезаурус) и проверка (ФСА) — разные задачи. Отдельно решить,
  прогоняем ли подобранный РД ещё и через ФСА перед отправкой в LiteMark.

### 11.6. УПД от LiteMark

Сейчас `POST /orders/{id}/result` принимает `object_key`, `file_name`, `content_type`, `size_bytes`,
`message` — **поля под УПД нет**.

Нужно:

1. Добавить в контракт `upd_number` и согласовать, приходит ли сам документ УПД отдельным объектом
   в MinIO или лежит внутри `result.zip`. Отразить в `integration_guide.md`.
2. **Пересмотреть хранение.** Сейчас УПД пишется в `order.processing_info` форматированной строкой:

   ```python
   order.processing_info = f'{company.title} ({company.inn}) <br> УПД: {upd_number}'
   ```

   `processing_info` — это `String(100)`, при том что `ProcessingCompany.title` — `String(255)`,
   а `inn` — `String(20)`. Строка легко перевалит за 100 символов, и Postgres ответит
   `value too long for type character varying(100)`; обработчик поймает это общим `except` и вернёт
   500. Пока УПД вводит человек, проблема всплывает редко — но если УПД начнёт приходить
   автоматически, упрёмся быстро. **`upd_number` стоит вынести в отдельную колонку**, а не хранить
   в размеченной строке, которую потом надо парсить.
3. Проверка в `process_order()` (`if not order.processing_info`) должна учитывать, что УПД теперь
   может прийти от LiteMark, а не только от оператора.

### 11.7. Вопрос, который стоит уточнить

В инструкции руководителя шаг 8: «если клиентом **в комментарии** к заказу не был указан оператор
ЭДО, отличный от ЭДО Лайт…». Но автоматизированные заказы по определению идут **без комментария** —
комментарий как раз и отправляет заказ в ручную CRM (раздел 2).

Значит, для автоматизированного потока ЭДО всегда берётся из поля `order.edo_type`
(дефолт `ЭДО-ЛАЙТ`), а не из комментария, и ветка «клиент указал другой ЭДО в комментарии»
для LiteMark недостижима. Стоит подтвердить, что это и имелось в виду.

---

## 13. Что осталось доделать

Разделено на две очереди: без первой интеграцию нельзя запустить вообще, вторая — новая
функциональность по итогам созвона (раздел 11).

### Очередь A — блокеры запуска

1. **Починить `ProxyFix`/`x_for`** (расхождение №2) — иначе IP-allowlist нельзя включить:
   пустой список отключает проверку, заполненный заблокирует все запросы.
2. **Убрать `app/migrations/` из `.gitignore`** или зафиксировать другой способ доставки схемы —
   сейчас ревизий нет в репозитории, на чистом клоне схему накатить нечем.
3. **Переписать раздел о подписи в `integration_guide.md`** под фактическую схему
   `sha256(secret\ntimestamp\nnonce)` (расхождение №1) — у LiteMark на руках документ с HMAC,
   который коду не соответствует.
4. **Определиться с HTTP-кодами `result`** (расхождение №4): сейчас несовпадение `object_key`
   и отсутствие файла в MinIO отдаются как HTTP 200. Синхронизировать с гайдом.
5. **Подключить `init_minio_integrations.sh`** к compose или к деплой-инструкции.

### Очередь B — новые требования от 18.08.2026

6. **Таймаут обработки 2 суток + уведомление LiteMark с подтверждением** (п. 11.4).
   Самое крупное: требует решения push/pull с LiteMark, планировщика, разведения
   `confirmation_timeout` и `processing_timeout`, признака «уведомлён/подтверждено» на заказе.
   Закрывает заодно проблемы 1 и 2 из раздела 8.
7. **Преподготовка: подбор РД через Тезаурус** (п. 11.5). Новый этап до пула выдачи; заказ без РД
   не должен быть eligible для `claim_new_orders()`. Не подобралось → в проблему.
   Отдельно решить, прогонять ли подобранный РД через ФСА (`app/fsa/` уже готов).
8. **УПД от LiteMark** (п. 11.6): поле `upd_number` в контракте `/result`, согласовать способ
   передачи самого документа, **вынести `upd_number` в отдельную колонку** вместо форматированной
   строки в `processing_info` (`String(100)` — реальный риск `value too long`).
9. **Согласовать индикацию в UI** с новыми таймаутами (п. 8, проблема 3 и п. 11.4):
   `AUTOMATED_EXTERNAL_CONFIRMATION_OVERDUE_SECONDS` — про подтверждение выдачи, для 2 суток
   обработки нужен свой бейдж.
10. **Уточнить вопрос по ЭДО** (п. 11.7) — ветка «клиент указал другой ЭДО в комментарии»
    для автоматизированного потока недостижима by design.

### Очередь C — хвосты

11. `helper_auto_problem_cancel_order()` в `views/crm/helpers.py` — единственная legacy-выборка
    без фильтра `LEGACY_CRM_ORDER_FILTER_SQL`: автоотмена через ~148 ч заденет и автоматизированные
    заказы. **С новым правилом это стало важнее**: заказы будут попадать в `MANAGER_PROBLEM`
    штатно и часто (через 2 суток), и у оператора будет ~6 суток до автоотмены. Подтвердить,
    что такое поведение устраивает.
12. Мёртвый код: `count_available_orders()` и `_pick_processing_company_payload()` (единичный,
    в отличие от используемого `_pick_processing_company_payload_map()`) не вызываются.
    Первую стоит не удалить, а задействовать для честного `X-Orders-Remaining`.

### Сделано

- ~~Обновить гайд: `replay_nonce`, 500-е коды, поведение `X-Orders-Remaining`, исправить
  `accept` в чек-листе dev-стенда.~~ — см. расхождения №3, №5, №6.

---

## 14. Карта файлов

```
app/
├── external_processors/            # модель обработчика: конфиг, схемы, CRUD
│   ├── config.py                   # дефолты ttl/nonce/batch/timeout
│   ├── schemas.py                  # pydantic-валидация
│   └── service.py                  # CRUD, генерация key_id/secret, сериализация
├── views/
│   ├── api/
│   │   ├── integrations.py         # 4 webhook-ручки, подпись, nonce, rate limit
│   │   └── integration_service.py  # выдача, accept/status/result, таймауты, аудит
│   ├── crm_automated/
│   │   ├── dashboard.py            # роуты доски
│   │   └── service.py              # выборки, доска, действия оператора
│   └── main/
│       └── external_processors.py  # админский CRUD-API
├── models.py                       # ExternalProcessor, OrderProcessedLog, поля Order
├── settings/commands.py            # CLI backfill_is_automated_crm
├── utilities/
│   ├── support.py                  # resolve_automated_crm_flag, is_automated_crm_order
│   ├── download.py                 # get_order_download_payload — исходный zip в base64
│   └── minio_service/services.py   # S3Service.object_exists
├── templates/crm_automated_v1/     # доска: карточки, логи, техинфо
└── templates/admin/external_processors/

minio_setup/
├── init_minio_integrations.sh      # создание ограниченных пользователей MinIO
└── minio_integrations.example.conf

docs/
├── litemark-integration.md         # этот файл
└── fsa-portal-integration.md       # отдельная интеграция с реестром ФСА
```
