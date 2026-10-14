# Локальный справочник Tezaurus

Временный источник данных для Markineris при `TEZAURUS_SYNC_ENABLED=0`, без
обращения к API Tezaurus. Снимки взяты
из продового Redis Markineris; ревизии и время последней синхронизации сохранены в
`data/versions.json` (`synced_at`: `2026-10-06T14:20:59+00:00`).

| Файл | Содержимое |
| --- | --- |
| `data/clothes_tnved.json` | ТН ВЭД одежды: `common` — 87 типов, `underwear` — 122 типа; тип → пол → коды и описания |
| `data/colors.json` | 127 цветов |
| `data/countries.json` | Страны для пользовательских и наших РД |
| `data/processing_companies.json` | 10 фирм, их активность, категории и `rf`/`import` |
| `data/versions.json` | Ревизии исходных словарей |

При `TEZAURUS_SYNC_ENABLED=0` `TezaurusCacheService` читает runtime-снимок через
`LocalTezaurusRepository`; если runtime-снимок недоступен или неполный,
используются эти seed-файлы. Остальные вызовы `runtime_catalogs.py` остаются
прежними. Изменение seed-файлов требует развёртывания новой версии приложения.
Для обычной одежды и нижнего белья эти данные используются также при проверке
Excel-загрузки и совместимости позиций при копировании заказа.

Выбор фирмы повторяет алгоритм соседнего проекта Tezaurus: для пары
`category/origin` берутся только активные подходящие фирмы, их идентификаторы
перемешиваются, и каждая фирма выдаётся один раз за цикл. Новый цикл не начинается
с фирмы, выданной последней в предыдущем цикле. Состояние каждой пары хранится в
Redis по ключу `tezaurus_fallback:processing_companies:selection:<category>:<origin>`;
операция `WATCH/MULTI` не даёт двум воркерам выбрать одну позицию одновременно.
Существующее наследование фирмы из карточек того же клиента сохраняется.

При `TEZAURUS_SYNC_ENABLED=1` приложение возвращается к прежнему режиму: читает
Redis-кэш Tezaurus, опрашивает API для его обновления и запрашивает фирму через API.
Если список стран в Redis пуст или недоступен, проверки стран используют этот
локальный снимок, затем старые списки из `settings`. После смены флага перезапустите
приложение, воркеры и планировщик. Старые данные Redis не удаляются.

Если внешний Tezaurus недоступен при `TEZAURUS_SYNC_ENABLED=1`, рабочие справочники
продолжают читаться из последнего Redis-кэша. Синхронизация будет логировать ошибку,
но не очищает Redis. Назначение обрабатывающей фирмы для карточек в этом режиме
остаётся API-запросом в Tezaurus; при сбое пользовательское действие получает
контролируемую ошибку, а транзакция откатывается.

## Runtime-снимок из MinIO

Файлы в `data/` остаются seed-версией в git. Актуальный runtime-снимок хранится в
MinIO bucket `static`: manifest по умолчанию лежит в
`tezaurus_fallback/current/manifest.json`, сами JSON-файлы — в версионированном
префиксе `tezaurus_fallback/snapshots/<revisions>/`. Manifest обновляется последним,
поэтому загрузчик не должен увидеть частично записанный набор.

При старте контейнера `entrypoint.sh` выполняет:

```bash
python3 -m tezaurus_fallback.s3_snapshot restore
```

Если manifest или файлы недоступны, сервис продолжает стартовать и использует seed
из `data/`. Если restore успешен, файлы пишутся в
`TEZAURUS_FALLBACK_RUNTIME_DATA_DIR` (`/app/runtime/tezaurus_fallback/data` по
умолчанию), а `LocalTezaurusRepository` читает уже их.

Ежедневная задача `export_tezaurus_fallback_snapshot_task` выгружает текущий Redis
Tezaurus в MinIO. Расписание задаёт `TEZAURUS_FALLBACK_SNAPSHOT_CRON`, включение —
`TEZAURUS_FALLBACK_SNAPSHOT_ENABLED`.
