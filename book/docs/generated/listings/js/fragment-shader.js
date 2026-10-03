// web/video.js, lines 84-113
vec4 colour(vec2 p) {
    float index = floor(texture2D(pixels, (p + 0.5) / source).r * 255.0 + 0.5);
    float row = floor(texture2D(rows, vec2((p.y + 0.5) / source.y, 0.5)).r * 255.0 + 0.5);
    float entry = row * palette.x + index;
    float line = floor((entry + 0.5) / palette.x);
    return texture2D(palettes, (vec2(entry - line * palette.x, line) + 0.5) / palette);
}

void main() {
    vec2 at = vec2(gl_FragCoord.x, box.y - gl_FragCoord.y);
    vec2 texel = at * enlarged / box - 0.5;
    vec2 first = clamp(floor(texel), vec2(0.0), enlarged - 1.0);
    vec2 second = min(first + 1.0, enlarged - 1.0);
    vec2 blend = clamp(texel - first, 0.0, 1.0);
    vec2 p0 = floor((first + 0.5) / factor);
    vec2 p1 = floor((second + 0.5) / factor);

    vec4 c = colour(p0);
    if (p1.x != p0.x) {
        c = mix(c, colour(vec2(p1.x, p0.y)), blend.x);
    }
    if (p1.y != p0.y) {
        vec4 below = colour(vec2(p0.x, p1.y));
        if (p1.x != p0.x) {
            below = mix(below, colour(p1), blend.x);
        }
        c = mix(c, below, blend.y);
    }
    gl_FragColor = vec4(c.rgb, 1.0);
}`;
