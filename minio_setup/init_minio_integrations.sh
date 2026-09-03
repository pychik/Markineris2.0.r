#!/bin/sh
set -eu

TAB=$(printf '\t')
CR=$(printf '\r')

log() {
  printf '%s\n' "$*"
}

trim() {
  value=$1

  while :; do
    case "$value" in
      " "*) value=${value#?} ;;
      "$TAB"*) value=${value#?} ;;
      "$CR"*) value=${value#?} ;;
      *) break ;;
    esac
  done

  while :; do
    case "$value" in
      *" ") value=${value%?} ;;
      *"$TAB") value=${value%?} ;;
      *"$CR") value=${value%?} ;;
      *) break ;;
    esac
  done

  printf '%s' "$value"
}

lower_ascii_char() {
  case "$1" in
    A) printf 'a' ;;
    B) printf 'b' ;;
    C) printf 'c' ;;
    D) printf 'd' ;;
    E) printf 'e' ;;
    F) printf 'f' ;;
    G) printf 'g' ;;
    H) printf 'h' ;;
    I) printf 'i' ;;
    J) printf 'j' ;;
    K) printf 'k' ;;
    L) printf 'l' ;;
    M) printf 'm' ;;
    N) printf 'n' ;;
    O) printf 'o' ;;
    P) printf 'p' ;;
    Q) printf 'q' ;;
    R) printf 'r' ;;
    S) printf 's' ;;
    T) printf 't' ;;
    U) printf 'u' ;;
    V) printf 'v' ;;
    W) printf 'w' ;;
    X) printf 'x' ;;
    Y) printf 'y' ;;
    Z) printf 'z' ;;
    *) printf '%s' "$1" ;;
  esac
}

slugify() {
  value=$1
  result=''
  last_was_dash=0

  while [ -n "$value" ]; do
    char=${value%"${value#?}"}
    value=${value#?}
    char=$(lower_ascii_char "$char")

    case "$char" in
      [a-z0-9])
        result="${result}${char}"
        last_was_dash=0
        ;;
      *)
        if [ -n "$result" ] && [ "$last_was_dash" -eq 0 ]; then
          result="${result}-"
          last_was_dash=1
        fi
        ;;
    esac
  done

  case "$result" in
    *-) result=${result%-} ;;
  esac

  printf '%s' "$result"
}

resolve_value() {
  raw_value=$(trim "$1")

  case "$raw_value" in
    @*)
      file_path=${raw_value#@}
      ;;
    file:*)
      file_path=${raw_value#file:}
      ;;
    *)
      printf '%s' "$raw_value"
      return 0
      ;;
  esac

  if [ ! -f "$file_path" ]; then
    log "Config secret file not found: $file_path"
    return 1
  fi

  secret_value=''
  if IFS= read -r secret_value < "$file_path"; then
    :
  fi

  case "$secret_value" in
    *"$CR") secret_value=${secret_value%?} ;;
  esac

  printf '%s' "$secret_value"
}

normalize_prefix() {
  prefix=$(trim "$1")
  prefix=${prefix#/}
  prefix=${prefix%/}
  printf '%s' "$prefix"
}

resolve_config_file() {
  requested_path=${1:-}

  if [ -n "$requested_path" ]; then
    if [ -f "$requested_path" ]; then
      printf '%s' "$requested_path"
      return 0
    fi

    log "Requested MinIO integrations config was not found: $requested_path"
    return 1
  fi

  for candidate in \
    /minio_setup/minio_integrations.local.conf \
    /minio_setup/minio_integrations.conf \
    /run/secrets/minio_integrations.conf
  do
    if [ -f "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done

  return 1
}

write_upload_only_policy() {
  policy_file=$1
  bucket_name=$2
  object_resource=$3

  cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "$object_resource"
      ]
    }
  ]
}
EOF
}

write_readonly_policy() {
  policy_file=$1
  bucket_name=$2
  object_resource=$3
  prefix=$4

  if [ -n "$prefix" ]; then
    cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "$prefix",
            "$prefix/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "$object_resource"
      ]
    }
  ]
}
EOF
    return 0
  fi

  cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "$object_resource"
      ]
    }
  ]
}
EOF
}

write_readwrite_policy() {
  policy_file=$1
  bucket_name=$2
  object_resource=$3
  prefix=$4

  if [ -n "$prefix" ]; then
    cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "$prefix",
            "$prefix/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "$object_resource"
      ]
    }
  ]
}
EOF
    return 0
  fi

  cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": [
        "arn:aws:s3:::$bucket_name"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "$object_resource"
      ]
    }
  ]
}
EOF
}

write_policy_file() {
  policy_file=$1
  bucket_name=$2
  prefix=$3
  access_mode=$4

  object_resource="arn:aws:s3:::$bucket_name/*"
  if [ -n "$prefix" ]; then
    object_resource="arn:aws:s3:::$bucket_name/$prefix/*"
  fi

  case "$access_mode" in
    upload-only)
      write_upload_only_policy "$policy_file" "$bucket_name" "$object_resource"
      ;;
    readonly)
      write_readonly_policy "$policy_file" "$bucket_name" "$object_resource" "$prefix"
      ;;
    readwrite)
      write_readwrite_policy "$policy_file" "$bucket_name" "$object_resource" "$prefix"
      ;;
    *)
      log "Unsupported access mode '$access_mode'. Expected one of: upload-only, readonly, readwrite"
      return 1
      ;;
  esac
}

ensure_minio_identity() {
  integration_name=$1
  minio_user=$2
  minio_password=$3
  bucket_name=$4
  prefix=$5
  access_mode=$6

  policy_name=$(slugify "$integration_name-$access_mode")
  if [ -z "$policy_name" ]; then
    policy_name=$(slugify "$minio_user-$bucket_name-$access_mode")
  fi

  if [ -z "$policy_name" ]; then
    log "Unable to build policy name for integration '$integration_name'"
    return 1
  fi

  policy_file="/tmp/${policy_name}.json"

  write_policy_file "$policy_file" "$bucket_name" "$prefix" "$access_mode"

  mc mb -p "s3/$bucket_name" >/dev/null 2>&1 || true

  if ! mc admin user info s3 "$minio_user" >/dev/null 2>&1; then
    mc admin user add s3 "$minio_user" "$minio_password"
  else
    log "MinIO user '$minio_user' already exists, reusing it and refreshing policy attachment"
  fi

  mc admin policy remove s3 "$policy_name" >/dev/null 2>&1 || true
  mc admin policy create s3 "$policy_name" "$policy_file"
  mc admin policy attach s3 "$policy_name" --user "$minio_user"
  rm -f "$policy_file"

  if [ -n "$prefix" ]; then
    log "Provisioned MinIO access for '$integration_name': bucket=$bucket_name prefix=$prefix mode=$access_mode user=$minio_user"
    return 0
  fi

  log "Provisioned MinIO access for '$integration_name': bucket=$bucket_name mode=$access_mode user=$minio_user"
}

main() {
  config_path=$(resolve_config_file "${1:-}") || {
    log "No MinIO integrations config found, skipping custom MinIO identities bootstrap"
    exit 0
  }

  log "Using MinIO integrations config: $config_path"

  line_no=0
  while IFS='|' read -r raw_name raw_user raw_password raw_bucket raw_prefix raw_mode raw_extra || [ -n "${raw_name:-}${raw_user:-}${raw_password:-}${raw_bucket:-}${raw_prefix:-}${raw_mode:-}${raw_extra:-}" ]; do
    line_no=$((line_no + 1))

    integration_name=$(trim "${raw_name:-}")
    if [ -z "$integration_name" ]; then
      continue
    fi

    case "$integration_name" in
      \#*)
        continue
        ;;
    esac

    if [ -n "$(trim "${raw_extra:-}")" ]; then
      log "Invalid config format at $config_path:$line_no. Expected 6 pipe-separated fields"
      exit 1
    fi

    minio_user=$(resolve_value "${raw_user:-}")
    minio_password=$(resolve_value "${raw_password:-}")
    bucket_name=$(trim "${raw_bucket:-}")
    prefix=$(normalize_prefix "${raw_prefix:-}")
    access_mode=$(trim "${raw_mode:-upload-only}")
    if [ -z "$access_mode" ]; then
      access_mode="upload-only"
    fi

    if [ -z "$minio_user" ] || [ -z "$minio_password" ] || [ -z "$bucket_name" ]; then
      log "Missing required values at $config_path:$line_no. Required: name|user|password|bucket|prefix|access_mode"
      exit 1
    fi

    ensure_minio_identity \
      "$integration_name" \
      "$minio_user" \
      "$minio_password" \
      "$bucket_name" \
      "$prefix" \
      "$access_mode"
  done < "$config_path"
}

main "$@"