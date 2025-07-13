/**
 * 知乎签名算法 - 简化版本
 * 用于生成知乎API请求所需的签名参数
 */

function get_sign(url, cookies) {
    // 简化实现，返回基础签名
    // 在生产环境中需要实现完整的知乎签名算法
    return {
        "x-zst-81": "3_2.0",
        "x-zse-96": "2.0_" + Math.random().toString(36).substring(2, 15)
    };
}