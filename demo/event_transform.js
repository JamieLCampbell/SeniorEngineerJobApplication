// Narrow synthetic event contract. Throwing preserves invalid payloads in the template error table.
function transform(input) {
  var event = JSON.parse(input);
  var fields = ["event_id", "customer_id", "event_type", "event_time"];
  var output = {};
  fields.forEach(function (field) {
    if (typeof event[field] !== "string" || !event[field].trim()) {
      throw new Error("missing_or_invalid:" + field);
    }
    output[field] = event[field].trim();
  });
  if (["view", "add_to_cart", "purchase"].indexOf(output.event_type) < 0) {
    throw new Error("unsupported:event_type");
  }
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(output.event_time) || isNaN(Date.parse(output.event_time))) {
    throw new Error("invalid:event_time");
  }
  if (new Date(output.event_time).toISOString() !== output.event_time.replace("Z", ".000Z")) {
    throw new Error("invalid:event_time"); // Date.parse can silently roll February 31 into March.
  }
  return JSON.stringify(output);
}
