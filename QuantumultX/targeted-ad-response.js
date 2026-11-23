/*
 * Quantumult X response-body filter for narrowly identified ad payloads.
 *
 * Only captured 12306 banner configuration, Cainiao ad-record responses,
 * Hellobike ad feeds, and the transit-app advertisement-configuration
 * envelope are modified. Other responses pass through unchanged unless an
 * explicitly recognized ad payload is found.
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
    } else if (requestUrl === "https://mobile.12306.cn/wxxcx/alipay/main/conf") {
        // The captured Alipay mini-program config marks ads_banner_conf entries with isShow=true.
        var bannerPages = payload && payload.data && payload.data.ads_banner_conf;
        if (Object.prototype.toString.call(bannerPages) === "[object Array]") {
            for (var p = 0; p < bannerPages.length; p++) {
                var page = bannerPages[p];
                var banners = page && page.conf;
                if (Object.prototype.toString.call(banners) !== "[object Array]") {
                    continue;
                }
                for (var b = 0; b < banners.length; b++) {
                    var banner = banners[b];
                    if (banner && typeof banner === "object" && banner.isShow === true) {
                        banner.isShow = false;
                        changed = true;
                    }
                }
            }
        }
    } else if (requestUrl.indexOf("https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.") === 0) {
        // Clear only ad-record arrays from the captured Cainiao ad APIs.
        var cainiaoMethod = requestUrl.substring(
            "https://netflow-mtop.cainiao.com/gw/mtop.cainiao.guoguo.nbnetflow.ads.".length
        ).split("/")[0];
        var cainiaoData = payload && payload.data;
        var isCainiaoAdRecord = function (item) {
            return item && typeof item === "object" &&
                Object.prototype.hasOwnProperty.call(item, "materialId") &&
                (Object.prototype.hasOwnProperty.call(item, "materialContentMapper") ||
                    Object.prototype.hasOwnProperty.call(item, "adUtArgs"));
        };
        var isCainiaoAdArray = function (items) {
            if (Object.prototype.toString.call(items) !== "[object Array]" || items.length === 0) {
                return false;
            }
            for (var a = 0; a < items.length; a++) {
                if (!isCainiaoAdRecord(items[a])) {
                    return false;
                }
            }
            return true;
        };

        if ((cainiaoMethod === "batch.show" || cainiaoMethod === "mshow") &&
            cainiaoData && typeof cainiaoData === "object") {
            for (var slotId in cainiaoData) {
                if (Object.prototype.hasOwnProperty.call(cainiaoData, slotId) && /^\d+$/.test(slotId) &&
                    isCainiaoAdArray(cainiaoData[slotId])) {
                    cainiaoData[slotId] = [];
                    changed = true;
                }
            }
        } else if ((cainiaoMethod === "show" || cainiaoMethod === "show.login") &&
            cainiaoData && isCainiaoAdArray(cainiaoData.result)) {
            cainiaoData.result = [];
            changed = true;
        }
    }

    if (changed) {
        resultBody = JSON.stringify(payload);
    }
} catch (e) {
    // Fail open: malformed or unrecognized content is never altered.
}

$done(resultBody);
