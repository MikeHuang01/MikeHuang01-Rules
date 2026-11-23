/*
 * Quantumult X response-body filter for narrowly identified ad payloads.
 *
 * Only the captured Hellobike ad feed shape and the captured transit-app
 * advertisement-configuration envelope are modified. Other responses pass
 * through byte-for-byte. Boolean advertisement switches in that envelope are
 * reset and ad-only metadata is cleared. The non-boolean `interstitialAd`
 * value is preserved because its meaning is not established by the capture.
 */
var originalBody = ($response && typeof $response.body === "string") ? $response.body : "";
var resultBody = originalBody;
var requestUrl = ($request && $request.url) ? String($request.url).split("?")[0].toLowerCase() : "";

try {
    var payload = JSON.parse(originalBody);
    var changed = false;

    if (requestUrl === "https://api.hellobike.com/api") {
        var data = payload && payload.data;
        var adm = data && data.adm;
        var looksLikeAdFeed = Object.prototype.toString.call(adm) === "[object Array]" && adm.length > 0;

        if (looksLikeAdFeed) {
            for (var i = 0; i < adm.length; i++) {
                var item = adm[i];
                if (!item || typeof item !== "object" || !item.impid ||
                    Object.prototype.toString.call(item.creative) !== "[object Array]" ||
                    item.creative.length === 0) {
                    looksLikeAdFeed = false;
                    break;
                }
            }
        }

        if (looksLikeAdFeed) {
            data.adm = [];
            changed = true;
        }
    } else if (requestUrl === "https://wx.mygolbs.com/wxbusserver/apidata.do") {
        // Signature of the captured CMD=115 ad-configuration response.
        // The same URL serves route/station operations with different schemas.
        var configKeys = [
            "indexAd", "lineAd", "interstitialAd", "bannerAd",
            "interstitialAd_ab", "bannerAd_ab", "welfareLineAd",
            "welfareLineAdText", "welfareLineAdType", "welfareLineAdPath",
            "welfareLineAdAppId", "ztAd", "ztAdCover", "tcAd", "tcAdUrl",
            "tcAdText", "adChannel", "bpAd", "bpId", "bpAdId", "bpPath",
            "bpText", "bpUrl", "alipayInsuranceAd", "cityNameAlias",
            "cityCode", "metroStatus", "qushixianAd", "adUuid", "status", "msg"
        ];
        var isAdConfig = payload && typeof payload === "object";

        for (var k = 0; isAdConfig && k < configKeys.length; k++) {
            if (!Object.prototype.hasOwnProperty.call(payload, configKeys[k])) {
                isAdConfig = false;
            }
        }

        if (isAdConfig) {
            var disabledSlots = [
                "indexAd", "lineAd", "bannerAd", "ztAdCover",
                "interstitialAd_ab", "bannerAd_ab", "welfareLineAd",
                "ztAd", "tcAd", "bpAd", "alipayInsuranceAd", "qushixianAd"
            ];
            for (var j = 0; j < disabledSlots.length; j++) {
                var slot = disabledSlots[j];
                if (typeof payload[slot] === "number" && payload[slot] !== 0) {
                    payload[slot] = 0;
                    changed = true;
                }
            }

            var clearedAdText = [
                "welfareLineAdText", "welfareLineAdPath", "welfareLineAdAppId",
                "tcAdUrl", "tcAdText", "adChannel", "bpId", "bpAdId",
                "bpPath", "bpText", "bpUrl", "adUuid"
            ];
            for (var s = 0; s < clearedAdText.length; s++) {
                var textKey = clearedAdText[s];
                if (typeof payload[textKey] === "string" && payload[textKey] !== "") {
                    payload[textKey] = "";
                    changed = true;
                }
            }
        }
    }

    if (changed) {
        resultBody = JSON.stringify(payload);
    }
} catch (e) {
    // Fail open: malformed or unrecognized content is never altered.
}

$done(resultBody);
