-- token_bucket.lua
-- KEYS[1]: rate_limit:{identifier}
-- ARGV[1]: rate (tokens per second)
-- ARGV[2]: capacity (bucket size)
-- ARGV[3]: now (current timestamp in seconds)
-- ARGV[4]: requested (tokens to consume, default 1)

local key = KEYS[1]
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4]) or 1

local last_refill = tonumber(redis.call("HGET", key, "last_refill"))
local tokens = tonumber(redis.call("HGET", key, "tokens"))

if last_refill == nil then
    tokens = capacity
    last_refill = now
else
    local delta = math.max(0, now - last_refill)
    local refilled = delta * rate
    tokens = math.min(capacity, tokens + refilled)
    last_refill = now
end

if tokens >= requested then
    tokens = tokens - requested
    redis.call("HSET", key, "last_refill", last_refill, "tokens", tokens)
    redis.call("EXPIRE", key, math.ceil(capacity / rate) + 60) -- Expire if unused for a while
    return {1, tokens} -- Allowed, Remaining
else
    local retry_after = (requested - tokens) / rate
    return {0, retry_after} -- Denied, Retry-After (seconds)
end
