import{b as i}from"./index-BB6GsKm2-v2.js";function n(r){const s=i();return s.isAdmin?!0:Array.isArray(r)?r.some(t=>s.permissionSet.has(t)):s.permissionSet.has(r)}export{n as c};
