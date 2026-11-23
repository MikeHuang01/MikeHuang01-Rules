/* Windows Script Host regression checks for targeted-ad-response.js.
 * Run from any directory with: cscript //nologo scripts/test-targeted-ad-response.js
 */
var fso = new ActiveXObject("Scripting.FileSystemObject");
var folder = fso.GetParentFolderName(WScript.ScriptFullName);
var sourceFile = fso.OpenTextFile(folder + "\\..\\QuantumultX\\targeted-ad-response.js", 1, false, 0);
var source = sourceFile.ReadAll();
sourceFile.Close();

// Legacy WSH JScript does not consistently expose JSON; fixture-only polyfills keep these tests portable.
if (typeof JSON === "undefined") {
    JSON = {};
}
JSON.parse = function (text) { return eval("(" + text + ")"); };
function quoteJson(text) {
    return "\"" + String(text).replace(/\\/g, "\\\\").replace(/\"/g, "\\\"")
        .replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t") + "\"";
}
JSON.stringify = function encode(value) {
    if (value === null) { return "null"; }
    if (typeof value === "string") { return quoteJson(value); }
    if (typeof value === "number" || typeof value === "boolean") { return String(value); }
    var parts = [];
    if (Object.prototype.toString.call(value) === "[object Array]") {
        for (var i = 0; i < value.length; i++) { parts.push(encode(value[i])); }
        return "[" + parts.join(",") + "]";
    }
    for (var key in value) {
        if (Object.prototype.hasOwnProperty.call(value, key)) {
            parts.push(quoteJson(key) + ":" + encode(value[key]));
        }
    }
    return "{" + parts.join(",") + "}";
};

var checks = 0;
function assert(condition, message) {
    if (!condition) {
        WScript.Echo("FAIL: " + message);
        WScript.Quit(1);
    }
    checks++;
}
function apply(url, body) {
    var result;
    var script = new Function("$response", "$request", "$done", source);
    script({ body: body }, { url: url }, function (updated) { result = updated; });
    return result;
}
function parsed(text) { return JSON.parse(text); }

var input = "{\"data\":{\"ads_banner_conf\":[{\"pageName\":\"home\",\"conf\":[{\"isShow\":true,\"imageUrl\":\"ad\"},{\"isShow\":false,\"imageUrl\":\"off\"}]},{\"conf\":[{\"isShow\":true}]}],\"index_banner_url\":\"keep\"}}";
var changed = parsed(apply("https://mobile.12306.cn/wxxcx/alipay/main/conf?x=1", input));
assert(changed.data.ads_banner_conf[0].conf[0].isShow === false, "12306 visible ad slot disabled");
assert(changed.data.ads_banner_conf[0].conf[1].isShow === false, "12306 already-disabled slot preserved");
assert(changed.data.ads_banner_conf[1].conf[0].isShow === false, "12306 all configured pages handled");
assert(changed.data.index_banner_url === "keep", "12306 non-slot config preserved");
var unrelated = "{\"data\":{\"stationList\":[{\"name\":\"test\"}]}}";
assert(apply("https://mobile.12306.cn/wxxcx/alipay/main/conf", unrelated) === unrelated, "unrecognized 12306 response passed through");

var batch = "{\"data\":{\"1820\":[{\"materialId\":\"fixture\",\"materialContentMapper\":{},\"id\":1}],\"2115\":[{\"materialId\":\"fixture2\",\"adUtArgs\":{},\"id\":2}],\"3000\":[{\"id\":3}],\"empty\":[]}}";
var batchResult = parsed(apply("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.batch.show/1.0", batch));
assert(batchResult.data["1820"].length === 0 && batchResult.data["2115"].length === 0, "Cainiao batch ad-record arrays cleared");
assert(batchResult.data["3000"].length === 1 && batchResult.data["empty"].length === 0, "Cainiao non-ad and empty arrays preserved");
var mshow = JSON.stringify({data: {"205": [{materialId: "fixture", materialContentMapper: {}, id: 5}], empty: [], other: [{materialId: "fixture", materialContentMapper: {}}]}});
var mshowResult = parsed(apply("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.mshow/1.0", mshow));
assert(mshowResult.data["205"].length === 0 && mshowResult.data["empty"].length === 0, "Cainiao mshow numeric ad slot cleared");
assert(mshowResult.data.other.length === 1, "Cainiao mshow nonnumeric data preserved");
var result = "{\"data\":{\"result\":[{\"materialId\":\"fixture\",\"materialContentMapper\":{},\"id\":4}]}}";
var login = parsed(apply("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.show.login/1.0", result));
assert(login.data.result.length === 0, "Cainiao show.login ad records cleared");
assert(apply("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.show/1.0", "{\"data\":{\"result\":[]}}") === "{\"data\":{\"result\":[]}}", "Cainiao empty show result passed through unchanged");
assert(apply("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.other.show/1.0", result) === result, "Cainiao non-ad API passed through");

var bus = "{\"data\":{\"stationList\":[{\"name\":\"test\"}]}}";
assert(apply("https://wx.mygolbs.com/WxBusServer/ApiData.do?CMD=138", bus) === bus, "transit route/station response preserved");
var bikeEmpty = "{\"data\":{\"adm\":[]}}";
assert(apply("https://api.hellobike.com/api", bikeEmpty) === bikeEmpty, "empty HelloBike ad array preserved");

WScript.Echo("PASS: " + checks + " targeted response regression checks");
