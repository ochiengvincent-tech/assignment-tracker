module.exports = {
  testEnvironment: "jsdom",
  roots: ["<rootDir>/tests"],
  testMatch: ["**/*.test.[jt]s?(x)"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.js"],
  transform: { "^.+\\.[jt]sx?$": "babel-jest" },
  clearMocks: true,
};