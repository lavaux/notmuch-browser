const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = (_env, argv) => {
  const production = argv.mode === "production";
  return {
    entry: {
      boot: path.resolve(__dirname, "web/src/boot.js"),
      main: path.resolve(__dirname, "web/src/index.js"),
    },
    output: {
      path: path.resolve(__dirname, "src/notmuch_browser/static"),
      filename: production ? "assets/[name].[contenthash:8].js" : "assets/[name].js",
      publicPath: "/",
      clean: true,
    },
    devtool: production ? false : "source-map",
    module: {
      rules: [{ test: /\.css$/, use: [MiniCssExtractPlugin.loader, "css-loader"] }],
    },
    plugins: [
      new MiniCssExtractPlugin({
        filename: production ? "assets/[name].[contenthash:8].css" : "assets/[name].css",
      }),
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, "web/src/index.html"),
        title: "notmuch-browser",
        scriptLoading: "blocking",
        inject: "head",
      }),
    ],
    performance: { hints: false },
  };
};
