// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
// This file is automatically run by the Jest test runner before any tests execute.

// Polyfill for the 'window.URL.createObjectURL' function that plotly.js needs.
window.URL.createObjectURL = function() {};

// Polyfill for the 'HTMLCanvasElement.prototype.getContext' function
// This prevents the canvas-related errors from plotly.js
HTMLCanvasElement.prototype.getContext = () => {
    // return a mock context object
    return {};
};